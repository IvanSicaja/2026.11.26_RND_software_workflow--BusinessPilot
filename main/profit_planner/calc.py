"""Calculation engine: from materials to net profit per unit and startup capital.

All results are per product unit and in the reporting currency.

Price
    Base price either fixed (gross, incl. VAT) or production cost x (1 + markup).
    Extra services are added on top (net price of the service + VAT).
VAT
    B2C: VAT of the market country (destination principle - domestic sales, EU OSS and
    import VAT for deliveries from Switzerland / Western Balkans all end up at the
    destination rate). B2B: domestic sale -> market VAT; cross-border -> 0 % (reverse
    charge / export). Small-business exemption -> 0 % for domestic sales only.
Deductions from the gross price
    VAT, payment fee (% of gross + fixed), sales commission (% of gross), shipping,
    customs duty + clearance (B2C only, different customs territories), expected returns
    (return rate x (outbound + return shipping + handling)), production cost
    (materials incl. waste, labour, service labour, tool depreciation, fixed overhead).
Taxes
    Social contributions (% of profit), profit / income tax on the rest, then
    distribution (dividend) tax when the profit is paid to the owner.
Startup cash
    Formation costs + max(min. share capital, tools + startup material stock)
    (share capital paid into the company can be used to buy tools and stock).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import schema as S
from .database import Database


class CalcError(Exception):
    pass


@dataclass
class Line:
    group: str      # Revenue, Deduction, Cost, Tax, Result, Info
    label: str
    amount: float
    note: str = ""


@dataclass
class Result:
    config_id: str = ""
    name: str = ""
    ok: bool = True
    error: str = ""
    warnings: list = field(default_factory=list)
    currency: str = "EUR"
    product_id: str = ""
    product_name: str = ""
    hq: str = ""
    company_type: str = ""
    legal_form: str = ""
    liability: str = ""
    market: str = ""
    sale_type: str = ""
    material_year: int | None = None
    vat_rate: float = 0.0
    gross_price: float = 0.0
    base_gross_price: float = 0.0
    services_gross: float = 0.0
    vat: float = 0.0
    net_revenue: float = 0.0
    materials: float = 0.0
    labour: float = 0.0
    service_labour: float = 0.0
    tool_depreciation: float = 0.0
    overhead: float = 0.0
    production_cost: float = 0.0
    payment_fee: float = 0.0
    commission: float = 0.0
    shipping: float = 0.0
    customs: float = 0.0
    returns: float = 0.0
    profit_before_tax: float = 0.0
    social: float = 0.0
    profit_tax: float = 0.0
    net_profit_company: float = 0.0
    distribution_tax: float = 0.0
    net_to_owner: float = 0.0
    margin_pct: float = 0.0
    break_even_gross: float | None = None
    annual_volume: int = 0
    annual_net_to_owner: float = 0.0
    share_capital: float = 0.0
    formation_costs: float = 0.0
    tools_cost: float = 0.0
    stock_cost: float = 0.0
    startup_total: float = 0.0
    payback_months: float | None = None
    lines: list = field(default_factory=list)
    material_lines: list = field(default_factory=list)   # (name, qty incl. waste, unit, cost)

    @property
    def status(self) -> str:
        if not self.ok:
            return "Error: " + self.error
        if self.warnings:
            return "OK (with warnings)"
        return "OK"

    @property
    def total_deductions(self) -> float:
        return self.gross_price - self.net_to_owner


def _num(row: dict, col: str, what: str, default=None, required: bool = True) -> float:
    v = row.get(col)
    if v is None or (isinstance(v, str) and v.strip() == ""):
        if default is not None or not required:
            return default
        raise CalcError(f"{what}: '{col}' is empty")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise CalcError(f"{what}: '{col}' is not a number ('{v}')")
    return float(v)


def _bool(v, default=False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() in ("yes", "y", "true", "1", "da", "ja")


class Engine:
    def __init__(self, db: Database):
        self.db = db
        self.rc = db.reporting_currency
        self.rates: dict[str, float] = {}
        for r in db[S.FX].rows:
            c, v = r.get("Currency"), r.get("Units per 1 EUR")
            if c and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                self.rates[str(c).upper()] = float(v)

    # -- helpers -------------------------------------------------------------
    def fx(self, amount: float, currency) -> float:
        cur = str(currency or "").strip().upper()
        if not cur:
            raise CalcError("currency is empty")
        if cur not in self.rates:
            raise CalcError(f"no exchange rate for currency '{cur}'")
        if self.rc not in self.rates:
            raise CalcError(f"no exchange rate for reporting currency '{self.rc}'")
        if cur == self.rc:
            return amount
        return amount / self.rates[cur] * self.rates[self.rc]

    def _get(self, sheet: str, key, what: str) -> dict:
        if key in (None, ""):
            raise CalcError(f"{what} is empty")
        r = self.db[sheet].find(key)
        if r is None:
            raise CalcError(f"{what} '{key}' not found in '{sheet}'")
        return r

    def region(self, code) -> str | None:
        r = self.db[S.COUNTRIES].find(code)
        return r.get("Region") if r else None

    def _route_candidates(self, origin: str, dest: str) -> list[tuple[str, str]]:
        ro, rd = self.region(origin), self.region(dest)
        out = []
        for o in (origin, ro, S.WILDCARD):
            for d in (dest, rd, S.WILDCARD):
                if o and d and (o, d) not in out:
                    out.append((o, d))
        return out

    def find_route(self, sheet: str, origin: str, dest: str) -> dict | None:
        rows = self.db[sheet].rows
        index = {}
        for r in rows:
            o, d = r.get("Origin"), r.get("Destination")
            if o is None or d is None:
                continue
            k = (str(o).strip().lower(), str(d).strip().lower())
            index.setdefault(k, r)
        for o, d in self._route_candidates(origin, dest):
            r = index.get((o.lower(), d.lower()))
            if r is not None:
                return r
        return None

    @staticmethod
    def _year_price(row: dict, years: list[int], year: int, what: str, warnings: list) -> float:
        def val(y):
            v = row.get(str(y))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
            if v not in (None, ""):
                raise CalcError(f"{what}: price for {y} is not a number ('{v}')")
            return None

        p = val(year) if year in years else None
        if p is not None:
            return p
        earlier = [y for y in years if y < year and val(y) is not None]
        if earlier:
            y = max(earlier)
            warnings.append(f"{what}: no price for {year}, used {y}")
            return val(y)
        raise CalcError(f"{what}: no price for {year} or any earlier year")

    def default_year(self) -> int | None:
        ys = self.db[S.MATERIALS].years
        return max(ys) if ys else None

    # -- main ------------------------------------------------------------------
    def calculate_all(self, only_active: bool = False) -> list[Result]:
        out = []
        for cfg in self.db[S.CONFIGS].rows:
            if only_active and not _bool(cfg.get("Active"), True):
                continue
            services = self.db[S.CONFIG_SERVICES].children(cfg.get("Configuration ID")) \
                if cfg.get("Configuration ID") else []
            out.append(self.calculate(cfg, services))
        return out

    def calculate(self, cfg: dict, services: list[dict] | None = None) -> Result:
        res = Result(config_id=str(cfg.get("Configuration ID") or ""), name=str(cfg.get("Name") or ""),
                     currency=self.rc)
        try:
            self._calculate(cfg, services or [], res)
        except CalcError as e:
            res.ok = False
            res.error = str(e)
        except (ZeroDivisionError, OverflowError, TypeError, ValueError) as e:  # defensive
            res.ok = False
            res.error = f"invalid data ({type(e).__name__}: {e})"
        return res

    def _calculate(self, cfg: dict, services: list[dict], res: Result):
        cid = res.config_id or "configuration"
        W = res.warnings
        L = res.lines
        product = self._get(S.PRODUCTS, cfg.get("Product ID"), "Product")
        hq = self._get(S.COUNTRIES, cfg.get("HQ Country"), "HQ country")
        mk = self._get(S.COUNTRIES, cfg.get("Market Country"), "Market country")
        ct = self._get(S.COMPANY_TYPES, cfg.get("Company Type ID"), "Company type")
        if str(ct.get("Country Code", "")).upper() != str(hq.get("Country Code")).upper():
            raise CalcError(f"company type '{ct.get('Company Type ID')}' is a legal form of "
                            f"{ct.get('Country Code')}, not of the HQ country {hq.get('Country Code')}")
        hq_code, mk_code = str(hq["Country Code"]), str(mk["Country Code"])
        hq_cur, mk_cur = hq.get("Currency"), mk.get("Currency")
        pid = str(product["Product ID"])

        res.product_id, res.product_name = pid, str(product.get("Name") or pid)
        res.hq, res.market = hq_code, mk_code
        res.company_type = str(ct.get("Company Type ID"))
        res.legal_form = str(ct.get("Legal Form") or "")
        res.liability = str(ct.get("Liability") or "")
        sale_type = str(cfg.get("Sale Type") or "B2C").upper()
        if sale_type not in S.SALE_TYPES:
            raise CalcError(f"sale type must be B2C or B2B, not '{cfg.get('Sale Type')}'")
        res.sale_type = sale_type

        volume = _num(cfg, "Annual Volume (units)", cid)
        if volume < 1:
            raise CalcError("annual volume must be at least 1")
        res.annual_volume = int(volume)

        year_v = cfg.get("Material Price Year")
        if year_v in (None, ""):
            year = self.default_year()
            if year is None:
                raise CalcError("no year columns in 'Materials'")
        else:
            year = int(_num(cfg, "Material Price Year", cid))
        res.material_year = year

        # ---- production cost --------------------------------------------------
        mat_years = self.db[S.MATERIALS].years
        materials = 0.0
        bom = self.db[S.PRODUCT_MATERIALS].children(pid)
        if not bom:
            W.append(f"product '{pid}' has no materials")
        for line in bom:
            m = self._get(S.MATERIALS, line.get("Material ID"), "Material")
            mname = f"Material '{m['Material ID']}'"
            qty = _num(line, "Quantity", f"{pid} / {m['Material ID']}")
            waste = line.get("Waste Override (%)")
            if waste in (None, ""):
                waste = _num(m, "Waste (%)", mname, default=0.0)
            else:
                waste = _num(line, "Waste Override (%)", f"{pid} / {m['Material ID']}")
            price = self._year_price(m, mat_years, year, mname, W)
            gross_qty = qty * (1 + waste / 100.0)
            cost = self.fx(gross_qty * price, m.get("Currency"))
            materials += cost
            res.material_lines.append((str(m.get("Name") or m["Material ID"]), gross_qty,
                                       str(m.get("Unit") or ""), cost))

        labour_rate = _num(hq, "Labour Cost per Hour", f"Country {hq_code}")
        labour = self.fx(_num(product, "Labour Hours", f"Product {pid}") * labour_rate, hq_cur)

        srv_years = self.db[S.SERVICES].years
        services_net = 0.0
        service_labour = 0.0
        for s in services:
            sv = self._get(S.SERVICES, s.get("Service ID"), "Service")
            sname = f"Service '{sv['Service ID']}'"
            q = _num(s, "Quantity", f"{cid} / {sv['Service ID']}")
            price = self._year_price(sv, srv_years, year, sname, W)
            services_net += self.fx(price * q, sv.get("Currency"))
            hours = _num(sv, "Labour Hours", sname, default=0.0)
            service_labour += self.fx(hours * q * labour_rate, hq_cur)

        tools_cost = 0.0
        tool_dep = 0.0
        for pt in self.db[S.PRODUCT_TOOLS].children(pid):
            t = self._get(S.TOOLS, pt.get("Tool ID"), "Tool")
            tname = f"Tool '{t['Tool ID']}'"
            q = _num(pt, "Quantity", f"{pid} / {t['Tool ID']}", default=1.0)
            price = self.fx(_num(t, "Purchase Price", tname) * q, t.get("Currency"))
            life = _num(t, "Useful Life (years)", tname)
            if life <= 0:
                raise CalcError(f"{tname}: useful life must be greater than 0")
            tools_cost += price
            tool_dep += price / life / volume

        ctname = f"Company type '{ct['Company Type ID']}'"
        overhead = self.fx(_num(ct, "Annual Fixed Costs", ctname, default=0.0), hq_cur) / volume
        base_cost = materials + labour + tool_dep + overhead
        production = base_cost + service_labour
        res.materials, res.labour, res.service_labour = materials, labour, service_labour
        res.tool_depreciation, res.overhead, res.production_cost = tool_dep, overhead, production

        # ---- VAT rate -------------------------------------------------------------
        domestic = hq_code.upper() == mk_code.upper()
        vat_rate = _num(mk, "VAT Standard Rate (%)", f"Country {mk_code}") / 100.0
        if sale_type == "B2B" and not domestic:
            vat_rate = 0.0
            W.append("B2B cross-border: no VAT charged (reverse charge / export)")
        if _bool(cfg.get("Small-Business VAT Exemption")):
            if domestic:
                vat_rate = 0.0
            else:
                W.append("small-business VAT exemption ignored: it only applies to domestic sales")
        res.vat_rate = vat_rate * 100

        # ---- price ----------------------------------------------------------------
        services_gross = services_net * (1 + vat_rate)
        base_gross_v = cfg.get("Base Gross Price (incl. VAT)")
        if base_gross_v not in (None, ""):
            pcur = cfg.get("Price Currency") or mk_cur
            base_gross = self.fx(_num(cfg, "Base Gross Price (incl. VAT)", cid), pcur)
            price_note = "fixed price"
        else:
            markup = _num(cfg, "Markup (%)", cid, default=0.0) / 100.0
            base_gross = base_cost * (1 + markup) * (1 + vat_rate)
            price_note = f"production cost + {markup * 100:g} % markup"
        gross = base_gross + services_gross
        net = gross / (1 + vat_rate)
        vat = gross - net
        res.base_gross_price, res.services_gross, res.gross_price = base_gross, services_gross, gross
        res.net_revenue, res.vat = net, vat
        if gross <= 0:
            raise CalcError("gross price is 0 - enter a price or a markup")

        # ---- sales costs ----------------------------------------------------------
        fee_pct, fee_fixed = 0.0, 0.0
        if cfg.get("Payment Method ID") not in (None, ""):
            pm = self._get(S.PAYMENT, cfg.get("Payment Method ID"), "Payment method")
            pmn = f"Payment method '{pm['Payment Method ID']}'"
            fee_pct = _num(pm, "Fee (%)", pmn, default=0.0) / 100.0
            fee_fixed = self.fx(_num(pm, "Fixed Fee", pmn, default=0.0), pm.get("Currency"))
        payment_fee = gross * fee_pct + fee_fixed
        comm_pct = _num(cfg, "Sales Commission (%)", cid, default=0.0) / 100.0
        commission = gross * comm_pct

        weight = _num(product, "Weight (kg)", f"Product {pid}")
        ship_row = self.find_route(S.SHIPPING, hq_code, mk_code)
        if ship_row is None:
            raise CalcError(f"no shipping rate from {hq_code} to {mk_code} (add a row in '{S.SHIPPING}')")
        sn = f"Shipping {ship_row.get('Origin')}->{ship_row.get('Destination')}"
        shipping = self.fx(_num(ship_row, "Cost per Shipment", sn)
                           + _num(ship_row, "Cost per kg", sn, default=0.0) * weight, ship_row.get("Currency"))

        customs = 0.0
        duty_rate, clearance = 0.0, 0.0
        customs_applies = False
        cross_customs = str(hq.get("Customs Territory") or hq_code).upper() != \
            str(mk.get("Customs Territory") or mk_code).upper()
        if cross_customs and sale_type == "B2C":
            cu = self.find_route(S.CUSTOMS, hq_code, mk_code)
            if cu is None:
                W.append(f"no customs rule {hq_code}->{mk_code}: duty assumed 0")
            else:
                cn = f"Customs {cu.get('Origin')}->{cu.get('Destination')}"
                duty_rate = _num(cu, "Duty Rate (%)", cn, default=0.0) / 100.0
                clearance = self.fx(_num(cu, "Clearance Fee", cn, default=0.0), cu.get("Currency"))
                customs = duty_rate * (net + shipping) + clearance
                customs_applies = True
        elif cross_customs:
            W.append("B2B export: customs duties assumed to be paid by the buyer")

        rr = _num(mk, "Return Rate (%)", f"Country {mk_code}", default=0.0) / 100.0
        handling = self.fx(_num(mk, "Return Handling Cost", f"Country {mk_code}", default=0.0), mk_cur)
        returns = rr * (2 * shipping + handling)

        res.payment_fee, res.commission, res.shipping = payment_fee, commission, shipping
        res.customs, res.returns = customs, returns

        pbt = net - production - payment_fee - commission - shipping - customs - returns
        res.profit_before_tax = pbt

        # ---- taxes ------------------------------------------------------------------
        social_pct = _num(ct, "Owner Social Contributions (%)", ctname, default=0.0) / 100.0
        tax_pct = _num(ct, "Profit / Income Tax Rate (%)", ctname) / 100.0
        dist_pct = _num(ct, "Distribution Tax Rate (%)", ctname, default=0.0) / 100.0
        social = max(0.0, pbt) * social_pct
        tax = max(0.0, pbt - social) * tax_pct
        net_company = pbt - social - tax
        dist = max(0.0, net_company) * dist_pct
        owner = net_company - dist
        res.social, res.profit_tax, res.net_profit_company = social, tax, net_company
        res.distribution_tax, res.net_to_owner = dist, owner
        res.margin_pct = owner / gross * 100 if gross else 0.0
        res.annual_net_to_owner = owner * volume

        # ---- break-even gross price (profit before tax = 0) ----------------------
        coeff = (1 - duty_rate) / (1 + vat_rate) - fee_pct - comm_pct
        fixed = production + fee_fixed + shipping + returns
        if customs_applies:
            fixed += duty_rate * shipping + clearance
        res.break_even_gross = fixed / coeff if coeff > 0 else None

        # ---- startup capital ------------------------------------------------------------
        stock_units = _num(cfg, "Startup Stock (units)", cid, default=0.0)
        res.share_capital = self.fx(_num(ct, "Min Share Capital", ctname, default=0.0), hq_cur)
        res.formation_costs = self.fx(_num(ct, "Formation Costs", ctname, default=0.0), hq_cur)
        res.tools_cost = tools_cost
        res.stock_cost = materials * stock_units
        res.startup_total = res.formation_costs + max(res.share_capital, tools_cost + res.stock_cost)
        monthly = res.annual_net_to_owner / 12
        res.payback_months = res.startup_total / monthly if monthly > 0 else None

        # ---- breakdown lines ------------------------------------------------------------
        L.append(Line("Revenue", "Base price (gross, incl. VAT)", base_gross, price_note))
        if services:
            L.append(Line("Revenue", "Extra services (gross, incl. VAT)", services_gross))
        L.append(Line("Revenue", "Gross price paid by customer", gross))
        L.append(Line("Deduction", f"VAT {vat_rate * 100:g} % ({mk_code})", -vat))
        L.append(Line("Revenue", "Net revenue (excl. VAT)", net))
        L.append(Line("Cost", f"Materials incl. waste (prices {year})", -materials))
        L.append(Line("Cost", f"Labour {_num(product, 'Labour Hours', pid):g} h x {labour_rate:g} {hq_cur}", -labour))
        if service_labour:
            L.append(Line("Cost", "Labour for extra services", -service_labour))
        L.append(Line("Cost", "Tool depreciation", -tool_dep))
        L.append(Line("Cost", "Company fixed costs (accounting, fees ...)", -overhead))
        L.append(Line("Deduction", f"Payment fee ({fee_pct * 100:g} % + fixed)", -payment_fee))
        if commission:
            L.append(Line("Deduction", f"Sales commission ({comm_pct * 100:g} %)", -commission))
        L.append(Line("Deduction", f"Shipping {hq_code} -> {mk_code}", -shipping))
        if customs_applies:
            L.append(Line("Deduction", f"Customs duty {duty_rate * 100:g} % + clearance", -customs))
        L.append(Line("Deduction", f"Expected returns ({rr * 100:g} %)", -returns))
        L.append(Line("Result", "Profit before tax", pbt))
        if social:
            L.append(Line("Tax", f"Owner social contributions ({social_pct * 100:g} %)", -social))
        L.append(Line("Tax", f"Profit / income tax ({tax_pct * 100:g} %)", -tax))
        L.append(Line("Result", "Net profit of the company", net_company))
        if dist:
            L.append(Line("Tax", f"Distribution tax on payout ({dist_pct * 100:g} %)", -dist))
        L.append(Line("Result", "NET TO OWNER", owner))
        if pbt < 0:
            W.append("loss: the price does not cover all costs")
