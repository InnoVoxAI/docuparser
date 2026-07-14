"""Unit tests do categorizador (T019, T023, Seção 6). Sem rede/disco."""

import pytest

from superlogica_download_map.categorizer import canonical_key, categorize

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("variant", ["AGUA", "Água", "água", "ÁGUA "])
def test_variants_share_canonical_key(variant):
    assert canonical_key(variant) == "agua"


def test_canonical_key_strips_punctuation_and_accents():
    assert canonical_key("Construção-Reformas") == "construcao reformas"
    assert canonical_key("Manut. de Jardim") == "manut de jardim"


@pytest.mark.parametrize("variant", ["AGUA", "Água", "água", "ÁGUA "])
def test_variants_map_to_same_folder(variant):
    assert categorize(variant) == "Água"


def test_family_grouping_manutencoes():
    assert categorize("Manut. de Piscina") == "Manutenções"
    assert categorize("Manutenção de Jardim") == "Manutenções"


def test_family_construcao_real_category():
    assert categorize("Construção-Reformas") == "Construção-Reformas"


def test_fallback_derived_title_case_for_unmatched_category():
    # "Condomínio" não casa nenhuma regra de família → pasta própria (Title Case).
    assert categorize("Condomínio") == "Condomínio"


def test_indeterminate_category_goes_to_revisar():
    from superlogica_download_map.config import FALLBACK_FOLDER

    assert categorize("") == FALLBACK_FOLDER
    assert categorize("   ") == FALLBACK_FOLDER
    assert categorize("!!!") == FALLBACK_FOLDER


def test_custom_family_rules_are_honored():
    rules = ((r"^gas", "Gás"),)
    assert categorize("Gas Encanado", family_rules=rules) == "Gás"


def test_aggregate_categories_distinct_with_proposed_folder():
    """Passada de reconhecimento (T033): categorias distintas + pasta proposta."""
    from superlogica_download_map.categorizer import aggregate_categories

    cells = [
        "Água - Conta mensal",
        "AGUA - leitura",
        "Construção-Reformas - IMPERMEABILIZACAO",
        "",  # sem categoria → ignorada
        "Condomínio - Taxa condominial",
    ]
    rows = aggregate_categories(cells)
    proposed = {cat: folder for cat, _key, folder in rows}
    assert set(proposed) == {"Água", "AGUA", "Construção-Reformas", "Condomínio"}
    # variantes caem na mesma pasta
    assert proposed["Água"] == "Água"
    assert proposed["AGUA"] == "Água"
    assert proposed["Construção-Reformas"] == "Construção-Reformas"
    assert proposed["Condomínio"] == "Condomínio"


# --- Calibração com dados reais (categorias_encontradas.csv) ------------------


def test_calibration_fixes_false_positives():
    # Bugs do dicionário genérico anterior, agora corrigidos:
    assert categorize("Eletrônica") == "Segurança"  # antes ia p/ Energia (por ^ele)
    assert categorize("Elevador Peças e Reparos") == "Manutenções"  # antes Energia
    assert categorize("Seguro Funcionários") == "Seguros"  # antes Segurança (por ^segur)


def test_calibration_groups_real_families():
    assert categorize("Manut. de Bombas") == "Manutenções"
    assert categorize("Energia Elétrica") == "Energia"
    assert categorize("Água e Esgoto") == "Água"
    assert categorize("CFTV") == "Segurança"
    assert categorize("Funcionários") == "Pessoal"


@pytest.mark.parametrize(
    "noise", ["- MAIO", "- 2025", "PARC 10/10", "de Bombas", "e Esgoto", "do Poço"]
)
def test_calibration_routes_extraction_noise_to_revisar(noise):
    from superlogica_download_map.config import FALLBACK_FOLDER

    assert categorize(noise) == FALLBACK_FOLDER
