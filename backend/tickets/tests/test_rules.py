import pytest
from ..rules import has_critical_keywords

# Probara si las palabras ingresadas en las tuplas obtienen un True de acuerdo a la lista CRITICAL KEYWORDS 
# @pytest.mark.parametrize("text, expected", [("Bloqueado", True), ("No tengo audio", False),("Tenemos UNA caída total", True),("PÉRDIDA DE DATOS", True)])
# def test_has_critical_keywords_detects_critical_text(text, expected):
#     assert has_critical_keywords(text) == expected

# Usaremos la manera mas corta y facil para probar estas palabras criticas
@pytest.mark.parametrize("text", [("Bloqueado"),("caida total"),("no funciona nada"),("perdida de datos"),("no puedo acceder"),("SEGURIDAD")])
def test_has_critical_keywords_detects_critical_text(text):
    assert has_critical_keywords(text) is True

# # Probara si las palabras ingresadas como text existen en la lista CRITICAL KEYWORDS  
# @pytest.mark.parametrize("text, expected", [("En espera", False), ("Es la tercera vez", False),("Tenemos UNA caída total", True),("PÉRDIDA DE DATOS", True),("Temblor",False),("",False),(None,False)])
# def test_has_critical_keywords_ignores_normal_text(text, expected):
#     assert has_critical_keywords(text) == expected

@pytest.mark.parametrize("text", [("En espera"),("Es la tercera vez"),("Temblor"),("perdida de cables"),("Apurate"),("Desbloqueado")])
def test_has_critical_keywords_ignores_normal_text(text):
    assert has_critical_keywords(text) is False