from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from app_paths import (
    APP_DIR,
    DEBUG_DIR,
    REFERENCES_DIR,
)
from capture import capture_window_region
from compare import compare_images
from project_store import load_config
from template_match import find_template
from window_finder import (
    WindowInfo,
    find_elite_window,
    get_current_desktop,
)


class Vision:
    def __init__(self) -> None:
        self.config = load_config()
        self.project_dir = APP_DIR
        self.references_dir = REFERENCES_DIR

    def _show_failed_comparison(
        self,
        *,
        current_image: Image.Image,
        reference_path: Path,
        reference_name: str,
        similarity: float,
    ) -> Path:
        """
        Erstellt bei einer fehlgeschlagenen Zustandserkennung
        ein Vergleichsbild und öffnet es im Bildbetrachter.

        Links:
            aktueller Ausschnitt aus Elite

        Rechts:
            bestes Referenzbild
        """

        debug_dir = DEBUG_DIR / "vision"

        debug_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        reference_image = Image.open(reference_path).convert("RGB")

        current_rgb = current_image.convert("RGB")

        # Falls sich die Bildgrößen unterscheiden,
        # wird das aktuelle Bild auf die Größe der Referenz gebracht.
        if current_rgb.size != reference_image.size:
            current_rgb = current_rgb.resize(
                reference_image.size,
                Image.Resampling.LANCZOS,
            )

        title_height = 70
        spacing = 10

        image_width = reference_image.width
        image_height = reference_image.height

        comparison = Image.new(
            "RGB",
            (
                image_width * 2 + spacing,
                image_height + title_height,
            ),
            "black",
        )

        comparison.paste(
            current_rgb,
            (
                0,
                title_height,
            ),
        )

        comparison.paste(
            reference_image,
            (
                image_width + spacing,
                title_height,
            ),
        )

        draw = ImageDraw.Draw(comparison)

        draw.text(
            (
                10,
                8,
            ),
            "Aktueller Elite-Ausschnitt",
            fill="white",
        )

        draw.text(
            (
                image_width + spacing + 10,
                8,
            ),
            f"Referenz: {reference_name}",
            fill="white",
        )

        draw.text(
            (
                10,
                35,
            ),
            (
                "Keine sichere Erkennung – "
                f"beste Übereinstimmung: "
                f"{similarity * 100:.2f} %"
            ),
            fill="white",
        )

        comparison_path = debug_dir / (
            f"{timestamp}_" f"{reference_name}_" f"{similarity * 100:.2f}.png"
        )

        comparison.save(comparison_path)

        print("Vision: Debug-Vergleich gespeichert: " f"{comparison_path}")

        try:
            subprocess.Popen(
                [
                    "xdg-open",
                    str(comparison_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        except OSError as exc:
            print(
                "Vision: Vergleichsbild konnte nicht "
                f"automatisch geöffnet werden: {exc}"
            )

        return comparison_path

    def _get_elite_window(self) -> WindowInfo:
        """
        Sucht das Elite-Fenster und prüft,
        ob es auf der aktiven Arbeitsfläche liegt.
        """

        window = find_elite_window()

        if window is None:
            raise RuntimeError("Elite-Fenster wurde nicht gefunden.")

        current_desktop = get_current_desktop()

        if window.desktop != current_desktop:
            raise RuntimeError(
                f"Elite läuft auf Arbeitsfläche "
                f"{window.desktop + 1}, "
                f"aktuell aktiv ist Arbeitsfläche "
                f"{current_desktop + 1}."
            )

        return window

    def _get_reference(
        self,
        reference_name: str,
    ) -> dict:
        """
        Liefert die Daten einer gespeicherten Referenz.
        """

        reference = self.config.get(
            "references",
            {},
        ).get(reference_name)

        if reference is None:
            raise KeyError(f"Referenz '{reference_name}' nicht gefunden.")

        return reference

    def _get_reference_path(
        self,
        reference: dict,
    ) -> Path:
        """
        Ermittelt den vollständigen Pfad zum Referenzbild.
        """

        reference_path = self.references_dir / str(reference["image"])

        if not reference_path.exists():
            raise FileNotFoundError("Referenzbild nicht gefunden: " f"{reference_path}")

        return reference_path

    def check(
        self,
        reference_name: str,
        *,
        threshold: float = 0.95,
    ) -> tuple[bool, float]:
        """
        Prüft eine Referenz an ihrer fest gespeicherten Position.

        Diese Methode verwendet keine Positionssuche.

        Rückgabe:
            tuple[bool, float]:
                - Treffer ja/nein
                - Ähnlichkeit zwischen 0.0 und 1.0
        """

        reference = self._get_reference(reference_name)

        reference_path = self._get_reference_path(reference)

        window = self._get_elite_window()

        image = capture_window_region(
            window=window,
            x=int(reference["x"]),
            y=int(reference["y"]),
            width=int(reference["width"]),
            height=int(reference["height"]),
        )

        similarity = compare_images(
            reference_path=reference_path,
            current_image=image,
        )

        matched = similarity >= threshold

        return matched, similarity

    def is_state(
        self,
        reference_name: str,
        *,
        threshold: float = 0.95,
    ) -> bool:
        """
        Prüft eine einzelne Referenz an ihrer
        fest gespeicherten Position.
        """

        matched, similarity = self.check(
            reference_name,
            threshold=threshold,
        )

        print(
            f"Vision: {reference_name} "
            f"{similarity * 100:.2f} % "
            f"{'MATCH' if matched else 'NO MATCH'}"
        )

        return matched

    def _find_menu_block(
        self,
        reference_names: list[str],
        *,
        extra_width: int = 200,
        extra_height: int = 200,
    ) -> tuple[Image.Image, int, int, float]:
        """
        Sucht den Menüblock innerhalb eines größeren Bereichs.

        Alle übergebenen Zustandsreferenzen werden als mögliche
        Suchvorlagen getestet. Der beste OpenCV-Treffer bestimmt
        die aktuelle Position des Menüblocks.

        Die Referenzen dürfen unterschiedliche gespeicherte
        X- und Y-Positionen besitzen. Breite und Höhe müssen
        jedoch identisch sein.

        Rückgabe:
            tuple:
                - aktuell gefundener Menüblock
                - X-Position im Elite-Fenster
                - Y-Position im Elite-Fenster
                - OpenCV-Ähnlichkeit
        """

        if not reference_names:
            raise RuntimeError("Es wurden keine Zustandsreferenzen übergeben.")

        first_reference = self._get_reference(reference_names[0])

        reference_x = int(first_reference["x"])

        reference_y = int(first_reference["y"])

        reference_width = int(first_reference["width"])

        reference_height = int(first_reference["height"])

        # Alle Referenzen eines Menüblocks müssen
        # dieselbe Bildgröße besitzen.
        #
        # Die gespeicherte Position darf abweichen,
        # da einzelne Referenzen im Wizard leicht
        # unterschiedlich gesetzt worden sein können.
        for reference_name in reference_names[1:]:
            reference = self._get_reference(reference_name)

            current_width = int(reference["width"])

            current_height = int(reference["height"])

            if current_width != reference_width or current_height != reference_height:
                raise RuntimeError(
                    "Alle Menüblock-Referenzen müssen "
                    "dieselbe Breite und Höhe besitzen. "
                    f"Abweichung bei "
                    f"'{reference_name}': "
                    f"{current_width}x{current_height}, "
                    f"erwartet wird "
                    f"{reference_width}x{reference_height}."
                )

        # Der Suchbereich wird gleichmäßig um die
        # Position der ersten Referenz vergrößert.
        #
        # Kleine Positionsabweichungen der anderen
        # Referenzen werden durch extra_width und
        # extra_height mit abgedeckt.
        search_x = reference_x - extra_width // 2

        search_y = reference_y - extra_height // 2

        search_width = reference_width + extra_width

        search_height = reference_height + extra_height

        window = self._get_elite_window()

        search_image = capture_window_region(
            window=window,
            x=search_x,
            y=search_y,
            width=search_width,
            height=search_height,
        )

        best_result = None
        best_finder_name: str | None = None

        # Da wir vorher nicht wissen, welcher Menüpunkt
        # markiert ist, werden alle Zustandsbilder als
        # Suchvorlage ausprobiert.
        for reference_name in reference_names:
            reference = self._get_reference(reference_name)

            reference_path = self._get_reference_path(reference)

            result = find_template(
                template_path=reference_path,
                search_image=search_image,
            )

            print(
                f"Vision: Positionssuche "
                f"{reference_name}: "
                f"{result.similarity * 100:.2f} % "
                f"bei x={result.x}, y={result.y}"
            )

            if best_result is None or result.similarity > best_result.similarity:
                best_result = result
                best_finder_name = reference_name

        if best_result is None:
            raise RuntimeError("Der Menüblock konnte nicht gesucht werden.")

        current_menu_block = search_image.crop(
            (
                best_result.x,
                best_result.y,
                best_result.x + reference_width,
                best_result.y + reference_height,
            )
        )

        absolute_x = search_x + best_result.x

        absolute_y = search_y + best_result.y

        print(
            f"Vision: Menüblock gefunden mit "
            f"{best_finder_name} "
            f"bei x={absolute_x}, y={absolute_y} "
            f"({best_result.similarity * 100:.2f} %)"
        )

        return (
            current_menu_block,
            absolute_x,
            absolute_y,
            float(best_result.similarity),
        )

    def get_state(
        self,
        *,
        prefix: str = "main_menu_block_",
        threshold: float = 0.95,
        extra_width: int = 200,
        extra_height: int = 200,
    ) -> tuple[str | None, float]:
        """
        Ermittelt den aktuell sichtbaren Menü-Zustand.

        Ablauf:
            1. Passende Zustandsreferenzen anhand des Präfix suchen.
            2. Einen größeren Bildschirmbereich aufnehmen.
            3. Mit OpenCV die aktuelle Position des Menüblocks finden.
            4. Den gefundenen Block gegen alle Zustände vergleichen.
            5. Den besten Zustand zurückgeben.

        Rückgabe:
            tuple[str | None, float]:
                - Name des erkannten Zustands oder None
                - höchste gefundene Ähnlichkeit
        """

        references = self.config.get(
            "references",
            {},
        )

        reference_names = sorted(
            reference_name
            for reference_name in references
            if reference_name.startswith(prefix)
        )

        if not reference_names:
            raise RuntimeError("Keine Referenzen mit Präfix " f"'{prefix}' gefunden.")

        (
            current_menu_block,
            absolute_x,
            absolute_y,
            locator_similarity,
        ) = self._find_menu_block(
            reference_names,
            extra_width=extra_width,
            extra_height=extra_height,
        )

        best_state: str | None = None
        best_similarity = 0.0
        best_reference_path: Path | None = None

        for reference_name in reference_names:
            reference = self._get_reference(reference_name)

            reference_path = self._get_reference_path(reference)

            similarity = compare_images(
                reference_path=reference_path,
                current_image=current_menu_block,
            )

            print(f"Vision: prüfe " f"{reference_name}: " f"{similarity * 100:.2f} %")

            if similarity > best_similarity:
                best_state = reference_name
                best_similarity = similarity
                best_reference_path = reference_path

        print(
            f"Vision: Menüposition "
            f"x={absolute_x}, y={absolute_y}; "
            f"OpenCV={locator_similarity * 100:.2f} %"
        )

        if best_similarity < threshold:
            print(
                "Vision: Zustand nicht erkannt. "
                f"Bester Treffer: {best_state} "
                f"mit {best_similarity * 100:.2f} %"
            )

            if best_state is not None and best_reference_path is not None:
                self._show_failed_comparison(
                    current_image=current_menu_block,
                    reference_path=best_reference_path,
                    reference_name=best_state,
                    similarity=best_similarity,
                )

            return None, best_similarity

        print(
            f"Vision: Zustand erkannt: "
            f"{best_state} "
            f"({best_similarity * 100:.2f} %)"
        )

        return best_state, best_similarity
