RETAIN_PATTERNS = [
    # Material name or formula
    r"\bmaterial[s]?\b", r"\bsample[s]?\b", r"\bcompound[s]?\b",
    r"\bceramic\b", r"\bbulk\b", r"\bpolycrystalline\b", r"\bsingle crystal\b", r"\bnanoparticle[s]?\b",
    r"\bthin film\b", r"\bpellet\b", r"\bingot[s]?\b", r"\bpowder[s]?\b",
    r"\bgrain boundary\b", r"\bgrain size\b", r"\bnanostructure\b",

    # Thermoelectric keywords
    r"\bZT\b", r"\bdimensionless figure of merit\b", r"\bfigure of merit\s*[:=]?\s*\d+(\.\d+)?\b",
    r"\bSeebeck coefficient\b", r"\bthermopower\b", r"\bS\s*=\s*[-+]?\d+(\.\d+)?\s*(μV/K|uV/K|V/K)\b",
    r"\belectrical conductivity\b", r"\bσ\s*=\s*[-+]?\d+(\.\d+)?\s*(S/m|Ω⁻¹m⁻¹)\b",
    r"\belectrical resistivity\b", r"\bρ\s*=\s*[-+]?\d+(\.\d+)?\s*(μΩ·cm|Ω·m|Ω·cm)\b",
    r"\bpower factor\b", r"\bPF\s*=\s*[-+]?\d+(\.\d+)?\s*(μW/cm·K²|mW/m·K²|W/m·K²)\b",
    r"\bthermal conductivity\b", r"\bκ\s*=\s*[-+]?\d+(\.\d+)?\s*(W/mK|W/m·K)\b",
    r"\blattice thermal conductivity\b", r"\belectronic thermal conductivity\b",
    r"\bHall coefficient\b", r"\bcarrier mobility\b", r"\bcarrier concentration\b",

    # Temperatures + units
    r"\b\d{2,4}\s*(K|°C|kelvin|degrees Celsius|Celsius)\b", r"\bat room temperature\b",
    r"\btemperature range\b", r"\bmeasured from .* to .* K\b", r"\bT\s*=\s*[0-9.]+K\b",
    r"\bincreasing temperature\b", r"\bhigh temperature region\b", r"\blow temperature behavior\b",
    r"\bRoom temperature\b", r"\bRT",

    # Structural descriptors
    r"\bspace group\b", r"\bSG\s*[:=]?\s*\w+\b", r"\bsymmetry\b",
    r"\bcrystal structure\b", r"\blattice structure\b", r"\bunit cell\b",
    r"\blattice constant[s]?\b", r"\blattice parameter[s]?\b",
    r"\ba\s*=\s*\d+(\.\d+)?\s*(Å|angstrom|nm)\b",
    r"\bb\s*=\s*\d+(\.\d+)?\s*(Å|angstrom|nm)\b",
    r"\bc\s*=\s*\d+(\.\d+)?\s*(Å|angstrom|nm)\b",
    r"\bangstrom\b", r"\bÅ\b",
    r"\bperovskite\b", r"\bskutterudite\b", r"\bzinc blende\b", r"\brhombohedral\b", r"\borthorhombic\b",
    r"\btetragonal\b", r"\bcubic\b", r"\bhexagonal\b", r"\btriclinic\b", r"\bmonoclinic\b",
    r"\blayered structure\b", r"\bquasi-one-dimensional\b", r"\bquasi-two-dimensional\b",
    r"\bquasi-three-dimensional\b",

    # Doping / composition
    r"\bdoping\b", r"\bdopant[s]?\b", r"\bsubstitution\b", r"\bsubstituted\b",
    r"\bdoped with\b", r"\bdop(ed|ing) sample\b", r"\bnominal composition\b",
    r"\bcarrier type\b", r"\bp-type\b", r"\bn-type\b", r"\bdegenerate\b", r"\bintrinsic\b",
    r"\bchemical formula\b", r"\bcomposition\b", r"\bstoichiometry\b",
    r"x\s*=\s*[0-9.]+", r"y\s*=\s*[0-9.]+", r"\bsolid solution\b", r"\balloy\b",

    # ELEMENT NAMES / COMMON DOPANTS
    r"\bAg\b", r"\bSb\b", r"\bBi\b", r"\bTe\b", r"\bSe\b", r"\bPb\b", r"\bNi\b", r"\bCo\b",
    r"\bDy\b", r"\bYb\b", r"\bRe\b", r"\bLa\b", r"\bPr\b", r"\bSm\b", r"\bEu\b", r"\bHo\b",
    r"\bCu\b", r"\bSn\b", r"\bMg\b", r"\bZn\b", r"\bMn\b", r"\bAl\b", r"\bFe\b", r"\bSi\b",
    r"\bGe\b", r"\bIn\b", r"\bGa\b", r"\bCd\b", r"\bHg\b", r"\bTl\b", r"\bBi\b", r"\bTe\b",
    r"\bSe\b", r"\bPb\b", r"\bNi\b",

    # EXPERIMENTAL METHODS (STRUCTURAL & THERMO)
    r"\bXRD\b", r"\bX-ray diffraction\b", r"\bdiffraction pattern\b", r"\bRietveld\b",
    r"\bSEM\b", r"\bscanning electron microscopy\b", r"\bFESEM\b",
    r"\bEDS\b", r"\bEDX\b", r"\bTEM\b", r"\btransmission electron microscopy\b",
    r"\bHall effect\b", r"\btransport measurement[s]?\b", r"\bthermal transport\b",
    r"\blaser flash\b", r"\b4-probe\b", r"\bspark plasma\b", r"\bmelt spinning\b",
    r"\barc melting\b", r"\bsintering\b",
    r"\bthermal analysis\b", r"\bDSC\b", r"\bTGA\b", r"\bDTA\b",

    # PHYSICAL MEASUREMENTS & PHENOMENA
    r"\bphonon scattering\b", r"\bgrain boundary scattering\b", r"\bbipolar conduction\b",
    r"\bdegenerate semiconductor\b", r"\bsemiconducting behavior\b", r"\bband gap\b", r"\bFermi level\b",
]