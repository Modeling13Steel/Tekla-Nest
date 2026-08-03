from __future__ import annotations

from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.i18n import available_languages, set_language, tr, tr_error


def setup_function():
    reset_config()
    load_config("/tmp/nonexistent_config_67890.yaml")
    set_language("en")


def teardown_function():
    set_language("en")
    reset_config()


def test_available_languages_include_english_and_portuguese():
    assert available_languages() == {"en": "English", "pt": "Português"}


def test_translation_switches_to_portuguese():
    set_language("pt")

    assert tr("menus.language") == "Idioma"
    assert tr("commands.calculate.text") == "Calcular"


def test_error_translation_switches_to_portuguese():
    set_language("pt")

    assert tr_error("No parts loaded.") == "Nenhuma peça carregada."
    assert (
        tr_error(
            "Failed to load parts CSV: "
            "CSV 'parts.csv' is missing required columns: ['perfil']"
        )
        == "Falha ao carregar CSV de peças: "
        "O CSV parts.csv não tem as colunas obrigatórias: ['perfil']."
    )


def test_license_error_translation_switches_to_portuguese():
    set_language("pt")

    assert (
        tr_error(
            "Cannot reach the license server.\n"
            "Internet access is required for first-time activation."
        )
        == "Não foi possível contactar o servidor de licenças.\n"
        "É necessário acesso à Internet para a primeira ativação."
    )


def test_translation_falls_back_to_key_for_missing_value():
    assert tr("missing.key") == "missing.key"


def test_config_can_load_default_language(tmp_path):
    reset_config()
    config = tmp_path / "config.yaml"
    config.write_text("app:\n  language: pt\n", encoding="utf-8")

    cfg = load_config(str(config))

    assert cfg.language == "pt"
