"""In-memory representation of the Excel database plus validation."""
from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass

from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from . import schema as S
from .schema import Col, SheetSpec

_TRUE = {"yes", "y", "true", "1", "da", "ja", "x", "oui", "si"}
_FALSE = {"no", "n", "false", "0", "ne", "nein", "non", ""}


def _parse_number(raw):
    """Accept numbers, '1 234,50', '1,234.50', '12.5%', 'CHF 20'. Return float or raise ValueError."""
    if isinstance(raw, bool):
        raise ValueError
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and (math.isnan(raw) or math.isinf(raw)):
            raise ValueError
        return float(raw)
    s = str(raw).strip().replace(" ", "").replace(" ", "").replace("'", "").replace("%", "")
    s = re.sub(r"^[A-Za-z]{3}", "", s)
    s = re.sub(r"[A-Za-z]{3}$", "", s)
    if not s:
        raise ValueError
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    v = float(s)
    if math.isnan(v) or math.isinf(v):
        raise ValueError
    return v


def coerce(col: Col, raw):
    """Convert a raw cell value to the column's type.

    Returns (value, error_message). On error the raw value is returned unchanged
    so that nothing the user typed is ever lost.
    """
    if isinstance(raw, str):
        raw = ILLEGAL_CHARACTERS_RE.sub("", raw)[:32000]
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None, None
    kind = col.kind
    if kind in (S.NUMBER, S.PERCENT, S.INTEGER):
        try:
            v = _parse_number(raw)
        except (ValueError, TypeError):
            return raw, f"'{raw}' is not a number"
        if kind == S.INTEGER:
            if abs(v - round(v)) > 1e-9:
                return raw, f"'{raw}' must be a whole number"
            v = int(round(v))
        elif v == int(v) and abs(v) < 1e15:
            v = int(v) if isinstance(raw, int) else float(v)
        return v, None
    if kind == S.BOOL:
        s = str(raw).strip().lower()
        if isinstance(raw, bool):
            return raw, None
        if s in _TRUE:
            return True, None
        if s in _FALSE:
            return False, None
        return raw, f"'{raw}' must be Yes or No"
    # text-like
    if isinstance(raw, float) and raw == int(raw):
        raw = int(raw)
    s = str(raw).strip()
    if kind == S.CHOICE:
        for c in col.choices:
            if c.lower() == s.lower():
                return c, None
        return s, f"'{s}' must be one of: {', '.join(col.choices)}"
    if kind in (S.REF, S.LOCATION) or col.name in ("Country Code", "Currency", "Customs Territory"):
        # identifiers: normalise country/currency codes to upper case
        if col.ref in (S.COUNTRIES, S.FX) or col.name in ("Country Code", "Currency", "Customs Territory"):
            return s.upper(), None
        if kind == S.LOCATION:
            for r in S.REGIONS:
                if r.lower() == s.lower():
                    return r, None
            return (s.upper() if len(s) <= 3 else s), None
    return s, None


def display(col: Col | None, value) -> str:
    if value is None:
        return ""
    if col is not None and col.kind == S.BOOL and isinstance(value, bool):
        return S.YES if value else S.NO
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def to_excel(col: Col | None, value):
    if value is None:
        return None
    if col is not None and col.kind == S.BOOL and isinstance(value, bool):
        return S.YES if value else S.NO
    if isinstance(value, float) and value == int(value) and abs(value) < 1e15:
        return int(value)
    return value


@dataclass
class Issue:
    level: str          # "error" or "warning"
    sheet: str
    row: int | None     # 0-based row index in table, None = sheet level
    column: str | None
    message: str

    def location(self) -> str:
        loc = self.sheet
        if self.row is not None:
            loc += f", row {self.row + 2}"  # Excel row number (header is row 1)
        if self.column:
            loc += f", column '{self.column}'"
        return loc

    def __str__(self):
        return f"[{self.level.upper()}] {self.location()}: {self.message}"


class Table:
    def __init__(self, spec: SheetSpec, rows: list[dict] | None = None,
                 years: list[int] | None = None, extra_columns: list[str] | None = None):
        self.spec = spec
        self.rows: list[dict] = rows if rows is not None else []
        self.years: list[int] = sorted(set(years or []))
        self.extra_columns: list[str] = list(extra_columns or [])

    # -- columns -----------------------------------------------------------
    @property
    def name(self) -> str:
        return self.spec.name

    def columns(self) -> list[str]:
        """All columns in display order: spec columns, year columns, preserved extra columns."""
        return self.spec.column_names + [str(y) for y in self.years] + self.extra_columns

    def col(self, name: str) -> Col | None:
        c = self.spec.col(name)
        if c is not None:
            return c
        y = S.is_year_header(name)
        if y is not None and self.spec.year_columns:
            return S.year_col(y)
        if name in self.extra_columns:
            return Col(name, S.TEXT, width=16, help="Extra column (kept as is, not used in calculations).")
        return None

    def add_year(self, year: int, copy_from: int | None = None, increase_pct: float = 0.0):
        if not self.spec.year_columns:
            raise ValueError(f"Sheet '{self.name}' has no year columns")
        if year in self.years:
            raise ValueError(f"Year {year} already exists")
        self.years = sorted(self.years + [year])
        for r in self.rows:
            val = None
            if copy_from is not None:
                src = r.get(str(copy_from))
                if isinstance(src, (int, float)) and not isinstance(src, bool):
                    val = round(src * (1 + increase_pct / 100.0), 4)
            r[str(year)] = val

    def remove_year(self, year: int):
        if year in self.years:
            self.years.remove(year)
            for r in self.rows:
                r.pop(str(year), None)

    # -- rows --------------------------------------------------------------
    def new_row(self) -> dict:
        r = {c: None for c in self.columns()}
        for c in self.spec.columns:
            if c.default is not None:
                r[c.name] = (c.default == S.YES) if c.kind == S.BOOL else c.default
        return r

    def find(self, key) -> dict | None:
        k = self.spec.key
        if k is None or key is None:
            return None
        ks = str(key).strip().lower()
        for r in self.rows:
            v = r.get(k)
            if v is not None and str(v).strip().lower() == ks:
                return r
        return None

    def keys(self) -> list[str]:
        k = self.spec.key
        if not k:
            return []
        return [str(r[k]) for r in self.rows if r.get(k) not in (None, "")]

    def children(self, parent_key) -> list[dict]:
        if not self.spec.parent:
            return []
        col = self.spec.parent[0]
        pk = str(parent_key).lower()
        return [r for r in self.rows if r.get(col) is not None and str(r.get(col)).lower() == pk]


class Database:
    def __init__(self):
        self.tables: dict[str, Table] = {name: Table(spec) for name, spec in S.SPECS.items()}

    def __getitem__(self, name: str) -> Table:
        return self.tables[name]

    def copy(self) -> "Database":
        return copy.deepcopy(self)

    # -- settings ----------------------------------------------------------
    def setting(self, name: str, default=None):
        r = self[S.SETTINGS].find(name)
        if r is None or r.get("Value") in (None, ""):
            return default
        return r.get("Value")

    def set_setting(self, name: str, value, description: str = ""):
        t = self[S.SETTINGS]
        r = t.find(name)
        if r is None:
            r = t.new_row()
            r["Setting"] = name
            r["Description"] = description
            t.rows.append(r)
        r["Value"] = value

    @property
    def reporting_currency(self) -> str:
        return str(self.setting("Reporting Currency", "EUR")).strip().upper()

    def ensure_default_settings(self):
        for name, value, desc in S.DEFAULT_SETTINGS:
            if self[S.SETTINGS].find(name) is None:
                self.set_setting(name, value, desc)

    # -- references --------------------------------------------------------
    def references_to(self, sheet: str, key) -> list[tuple[str, int]]:
        """All (sheet, row index) that reference `key` of `sheet`."""
        out = []
        ks = str(key).strip().lower()
        for t in self.tables.values():
            for c in t.spec.columns:
                if c.kind == S.REF and c.ref == sheet:
                    for i, r in enumerate(t.rows):
                        v = r.get(c.name)
                        if v is not None and str(v).strip().lower() == ks:
                            out.append((t.name, i))
        if sheet == S.COUNTRIES:
            for tname in (S.SHIPPING, S.CUSTOMS):
                for i, r in enumerate(self[tname].rows):
                    for c in ("Origin", "Destination"):
                        v = r.get(c)
                        if v is not None and str(v).strip().lower() == ks:
                            out.append((tname, i))
        return out

    def rename_key(self, sheet: str, old, new) -> int:
        """Rename a primary key and update every reference. Returns number of updated references."""
        if old is None or new is None or str(old) == str(new):
            return 0
        n = 0
        olds = str(old).strip().lower()
        for t in self.tables.values():
            for c in t.spec.columns:
                is_loc = sheet == S.COUNTRIES and c.kind == S.LOCATION
                if (c.kind == S.REF and c.ref == sheet) or is_loc:
                    for r in t.rows:
                        v = r.get(c.name)
                        if v is not None and str(v).strip().lower() == olds:
                            r[c.name] = new
                            n += 1
        return n

    def delete_cascade_children(self, sheet: str, key) -> int:
        """Delete link-table rows whose parent is (sheet, key). Returns count deleted."""
        n = 0
        ks = str(key).strip().lower()
        for t in self.tables.values():
            if t.spec.parent and t.spec.parent[1] == sheet:
                col = t.spec.parent[0]
                before = len(t.rows)
                t.rows = [r for r in t.rows if r.get(col) is None or str(r.get(col)).strip().lower() != ks]
                n += before - len(t.rows)
        return n

    def next_id(self, sheet: str, prefix: str | None = None) -> str:
        t = self[sheet]
        prefix = prefix if prefix is not None else (t.spec.id_prefix or "ID-")
        existing = {k.lower() for k in t.keys()}
        nums = []
        for k in t.keys():
            if k.lower().startswith(prefix.lower()):
                tail = k[len(prefix):]
                if tail.isdigit():
                    nums.append(int(tail))
        n = (max(nums) + 1) if nums else 1
        while True:
            cand = f"{prefix}{n:03d}"
            if cand.lower() not in existing:
                return cand
            n += 1

    def location_valid(self, value) -> bool:
        if value is None:
            return False
        v = str(value)
        if v == S.WILDCARD or v in S.REGIONS:
            return True
        return self[S.COUNTRIES].find(v) is not None

    # -- years -------------------------------------------------------------
    def all_years(self) -> list[int]:
        return sorted(set(self[S.MATERIALS].years) | set(self[S.SERVICES].years))

    def normalize(self):
        """Convert every cell to its column type (invalid values are kept as typed)."""
        for t in self.tables.values():
            cols = t.columns()
            for r in t.rows:
                for c in cols:
                    col = t.col(c)
                    if col is not None:
                        r[c], _e = coerce(col, r.get(c))

    # -- comparison helper ---------------------------------------------------
    def to_plain(self) -> dict:
        """Canonical representation used to verify that a saved file round-trips exactly."""
        out = {}
        for name, t in self.tables.items():
            cols = t.columns()
            rows = []
            for r in t.rows:
                row = []
                for c in cols:
                    v = to_excel(t.col(c), r.get(c))
                    if isinstance(v, str):
                        v = v.strip()
                        if v == "":
                            v = None
                    if isinstance(v, float) and v == int(v):
                        v = int(v)
                    row.append(v)
                if any(x is not None for x in row):
                    rows.append(tuple(row))
            out[name] = (tuple(cols), tuple(rows))
        return out

    # -- validation ----------------------------------------------------------
    def validate(self) -> list[Issue]:
        issues: list[Issue] = []
        for t in self.tables.values():
            issues.extend(self._validate_table(t))
        issues.extend(self._validate_cross())
        return issues

    def _validate_table(self, t: Table) -> list[Issue]:
        out = []
        spec = t.spec
        seen = {}
        for i, r in enumerate(t.rows):
            for cname in t.columns():
                c = t.col(cname)
                if c is None:
                    continue
                v = r.get(cname)
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    if c.required:
                        out.append(Issue("error", t.name, i, cname, "value is required"))
                    continue
                val, err = coerce(c, v)
                if err:
                    out.append(Issue("error", t.name, i, cname, err))
                    continue
                if c.kind in (S.NUMBER, S.PERCENT, S.INTEGER):
                    if c.min is not None and val < c.min:
                        out.append(Issue("error", t.name, i, cname, f"must be at least {display(c, c.min)}"))
                    if c.max is not None and val > c.max:
                        out.append(Issue("error", t.name, i, cname, f"must be at most {display(c, c.max)}"))
                if c.kind == S.REF and c.ref:
                    if self[c.ref].find(val) is None:
                        out.append(Issue("error", t.name, i, cname, f"'{val}' does not exist in '{c.ref}'"))
                if c.kind == S.LOCATION and not self.location_valid(val):
                    out.append(Issue("error", t.name, i, cname,
                                     f"'{val}' is not a country code, region ({', '.join(S.REGIONS)}) or *"))
            if spec.key:
                k = r.get(spec.key)
                if k not in (None, ""):
                    kl = str(k).strip().lower()
                    if kl in seen:
                        out.append(Issue("error", t.name, i, spec.key,
                                         f"duplicate ID '{k}' (also in row {seen[kl] + 2})"))
                    else:
                        seen[kl] = i
            elif spec.unique:
                vals = tuple(str(r.get(c)).strip().lower() for c in spec.unique)
                if all(r.get(c) not in (None, "") for c in spec.unique):
                    if vals in seen:
                        out.append(Issue("warning", t.name, i, spec.unique[-1],
                                         f"duplicate combination (also in row {seen[vals] + 2}); "
                                         f"quantities are added together" if t.name in (
                                             S.PRODUCT_MATERIALS, S.PRODUCT_TOOLS, S.CONFIG_SERVICES)
                                         else f"duplicate route (also in row {seen[vals] + 2}); first row is used"))
                    else:
                        seen[vals] = i
        return out

    def _validate_cross(self) -> list[Issue]:
        out = []
        rc = self.reporting_currency
        if self[S.FX].find(rc) is None:
            out.append(Issue("error", S.SETTINGS, None, "Value",
                             f"reporting currency '{rc}' is not in 'Exchange Rates'"))
        ct_t = self[S.COMPANY_TYPES]
        for i, r in enumerate(self[S.CONFIGS].rows):
            ct = ct_t.find(r.get("Company Type ID"))
            hq = r.get("HQ Country")
            if ct is not None and hq and str(ct.get("Country Code", "")).upper() != str(hq).upper():
                out.append(Issue("error", S.CONFIGS, i, "Company Type ID",
                                 f"company type '{r.get('Company Type ID')}' belongs to "
                                 f"{ct.get('Country Code')}, not to HQ country {hq}"))
        return out
