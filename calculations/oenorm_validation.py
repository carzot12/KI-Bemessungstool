from __future__ import annotations

"""Deterministische Zulässigkeitsprüfung für den engen V1-Anwendungsfall.

Die Tragfähigkeitsformeln bleiben in :mod:`calculations.stabduebel`. Dieses
Modul prüft ausschließlich Geometrie, Modellkonsistenz und die eindeutig
belegten österreichischen Regeln für Zug parallel zur Faser (alpha = 0°).
"""

from dataclasses import dataclass
from enum import Enum

from calculations.stabduebel import StabduebelInput, StabduebelResult


class NormProfile(str, Enum):
    OENORM = "OENORM"


class ValidationStatus(str, Enum):
    PASSED = "ERFÜLLT"
    FAILED = "NICHT ERFÜLLT"
    WARNING = "WARNUNG"
    UNVERIFIED = "NOCH NICHT VERIFIZIERT"


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    name: str
    status: ValidationStatus
    source: str
    message: str
    actual: float | None = None
    required: float | None = None
    unit: str = ""

    @property
    def passed(self) -> bool:
        return self.status is not ValidationStatus.FAILED


@dataclass(frozen=True, slots=True)
class TechnicalValidationResult:
    norm_profile: NormProfile
    checks: tuple[ValidationCheck, ...]

    @property
    def admissible(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failures(self) -> tuple[ValidationCheck, ...]:
        return tuple(
            check for check in self.checks
            if check.status is ValidationStatus.FAILED
        )

    @property
    def warnings(self) -> tuple[ValidationCheck, ...]:
        return tuple(
            check for check in self.checks
            if check.status in (ValidationStatus.WARNING, ValidationStatus.UNVERIFIED)
        )


EN_TABLE_85 = "ÖNORM EN 1995-1-1:2019, Tabelle 8.5"
EN_SECTION_86 = "ÖNORM EN 1995-1-1:2019, Abschnitt 8.6"
EN_SECTION_1044 = "ÖNORM EN 1995-1-1:2019, Abschnitt 10.4.4"
OENORM_B_86 = (
    "ÖNORM B 1995-1-1:2023, nationale Ergänzung zu Abschnitt 8.6"
)
GEOMETRY_SOURCE = "Geometrische Plausibilität des V1-Eingabemodells"


def _minimum(
    name: str,
    actual: float,
    required: float,
    source: str,
) -> ValidationCheck:
    ok = actual >= required
    return ValidationCheck(
        name=name,
        status=ValidationStatus.PASSED if ok else ValidationStatus.FAILED,
        source=source,
        message=(
            f"{actual:g} mm vorhanden; mindestens {required:g} mm erforderlich."
        ),
        actual=actual,
        required=required,
        unit="mm",
    )


def validate_oenorm(
    data: StabduebelInput,
    result: StabduebelResult | None = None,
) -> TechnicalValidationResult:
    """Prüft den aktuellen Zuglaschenstoß für alpha = 0°.

    ``result`` ist optional. Wird er angegeben, fließt auch das Ergebnis der
    vorhandenen sieben Tragfähigkeitsnachweise in das Gesamtergebnis ein.
    """

    d = data.dowel_diameter_d_mm
    count = data.rows_parallel_n * data.rows_perpendicular_m
    checks: list[ValidationCheck] = [
        _minimum("Achsabstand a1", data.a1_mm, 5.0 * d, EN_TABLE_85),
        _minimum("Achsabstand a2", data.a2_mm, 3.0 * d, EN_TABLE_85),
        _minimum(
            "Beanspruchter Endabstand a3,t",
            data.a3_t_mm,
            max(7.0 * d, 80.0),
            EN_TABLE_85,
        ),
        _minimum(
            "Unbeanspruchter Randabstand a4,c",
            data.a4_c_mm,
            3.0 * d,
            EN_TABLE_85,
        ),
    ]

    diameter_ok = 6.0 < d < 30.0
    checks.append(ValidationCheck(
        name="Stabdübeldurchmesser",
        status=ValidationStatus.PASSED if diameter_ok else ValidationStatus.FAILED,
        source=EN_SECTION_86,
        message=f"d = {d:g} mm; gefordert ist 6 mm < d < 30 mm.",
        actual=d,
        unit="mm",
    ))
    if d > 24.0 and diameter_ok:
        checks.append(ValidationCheck(
            name="Großer Stabdübeldurchmesser",
            status=ValidationStatus.WARNING,
            source=OENORM_B_86,
            message=f"d = {d:g} mm liegt im zu vermeidenden Bereich über 24 mm.",
            actual=d,
            required=24.0,
            unit="mm",
        ))

    checks.extend([
        ValidationCheck(
            name="Mindestanzahl Stabdübel",
            status=ValidationStatus.PASSED if count >= 2 else ValidationStatus.FAILED,
            source=OENORM_B_86,
            message=f"{count} Stabdübel vorhanden; mindestens 2 erforderlich.",
            actual=float(count),
            required=2.0,
            unit="Stück",
        ),
        ValidationCheck(
            name="Mindestanzahl Scherflächen",
            status=(
                ValidationStatus.PASSED
                if data.shear_planes_s >= 4
                else ValidationStatus.FAILED
            ),
            source=OENORM_B_86,
            message=(
                f"{data.shear_planes_s} Scherflächen vorhanden; "
                "mindestens 4 erforderlich."
            ),
            actual=float(data.shear_planes_s),
            required=4.0,
            unit="Stück",
        ),
        ValidationCheck(
            name="Scherflächen und innenliegende Stahlbleche",
            status=(
                ValidationStatus.PASSED
                if data.shear_planes_s == 2 * data.number_of_plates_ns
                else ValidationStatus.FAILED
            ),
            source=GEOMETRY_SOURCE,
            message=(
                f"{data.number_of_plates_ns} innenliegende Bleche ergeben im "
                f"V1-Modell {2 * data.number_of_plates_ns} Scherflächen; "
                f"eingegeben sind {data.shear_planes_s}."
            ),
        ),
        ValidationCheck(
            name="Rechnerisch unterstützter Anschlussfall",
            status=(
                ValidationStatus.PASSED
                if data.number_of_plates_ns in (1, 2)
                else ValidationStatus.FAILED
            ),
            source=(
                "calculations/stabduebel.py: getrennte zwei- und "
                "vierschnittige Rechenmodelle"
            ),
            message=(
                f"Rechenmodell: {data.connection_case}."
            ),
        ),
    ])

    dowel_fu_by_grade = {"S235": 360.0, "S275": 430.0, "S355": 510.0}
    expected_fu = dowel_fu_by_grade.get(data.dowel_steel_grade.upper())
    steel_ok = expected_fu is not None and abs(
        data.dowel_fu_k_n_mm2 - expected_fu
    ) <= 1e-9
    checks.append(ValidationCheck(
        name="Stabdübel-Stahlsorte und Zugfestigkeit",
        status=ValidationStatus.PASSED if steel_ok else ValidationStatus.FAILED,
        source=f"{OENORM_B_86}, Tabelle NA.8.4-E2",
        message=(
            f"{data.dowel_steel_grade}: fu,k = {data.dowel_fu_k_n_mm2:g} N/mm²"
            + (
                f"; erforderlich sind {expected_fu:g} N/mm²."
                if expected_fu is not None
                else "; diese Stahlsorte ist im V1-Normprofil nicht hinterlegt."
            )
        ),
        actual=data.dowel_fu_k_n_mm2,
        required=expected_fu,
        unit="N/mm²",
    ))

    required_height = 2.0 * data.a4_c_mm + (
        data.rows_perpendicular_m - 1
    ) * data.a2_mm
    checks.append(ValidationCheck(
        name="Anordnung im Querschnitt (Höhe)",
        status=(
            ValidationStatus.PASSED
            if required_height <= data.height_h_mm
            else ValidationStatus.FAILED
        ),
        source=GEOMETRY_SOURCE,
        message=(
            f"Die symmetrische Anordnung benötigt {required_height:g} mm; "
            f"vorhanden sind {data.height_h_mm:g} mm."
        ),
        actual=data.height_h_mm,
        required=required_height,
        unit="mm",
    ))

    required_width = 2.0 * data.side_thickness_t1_mm + (
        data.plate_thickness_ts_mm
        if data.number_of_plates_ns == 1
        else data.middle_thickness_t2_mm
        + 2.0 * data.plate_thickness_ts_mm
    )
    checks.append(ValidationCheck(
        name="Schichtaufbau im Querschnitt (Breite)",
        status=(
            ValidationStatus.PASSED
            if abs(required_width - data.width_b_mm) <= 1e-6
            else ValidationStatus.FAILED
        ),
        source=GEOMETRY_SOURCE,
        message=(
            f"Der modellierte Schichtaufbau ergibt {required_width:g} mm; "
            f"der Querschnitt besitzt {data.width_b_mm:g} mm."
        ),
        actual=data.width_b_mm,
        required=required_width,
        unit="mm",
    ))

    checks.extend([
        ValidationCheck(
            name="Unbeanspruchter Endabstand a3,c",
            status=ValidationStatus.UNVERIFIED,
            source=EN_TABLE_85,
            message="Im V1-Eingabemodell ist kein separater Wert a3,c vorhanden.",
        ),
        ValidationCheck(
            name="Beanspruchter Randabstand a4,t",
            status=ValidationStatus.UNVERIFIED,
            source=EN_TABLE_85,
            message="Im V1-Eingabemodell ist kein separater Wert a4,t vorhanden.",
        ),
        ValidationCheck(
            name="Bohrloch im Holz",
            status=ValidationStatus.UNVERIFIED,
            source=EN_SECTION_1044,
            message=(
                "d0 wird im Rechenkern als Stahlblech-Lochdurchmesser verwendet; "
                "ein separater Holz-Bohrlochdurchmesser fehlt."
            ),
        ),
    ])

    if result is not None:
        checks.append(ValidationCheck(
            name="Tragfähigkeitsnachweise",
            status=(
                ValidationStatus.PASSED if result.passed else ValidationStatus.FAILED
            ),
            source="calculations/stabduebel.py (anschlussfallabhängige Nachweise)",
            message=(
                f"Alle {len(result.checks)} rechnerisch geführten Nachweise sind erfüllt."
                if result.passed
                else f"Nicht erfüllt; maßgebend: {result.governing_check.name}."
            ),
        ))

    return TechnicalValidationResult(NormProfile.OENORM, tuple(checks))
