import pytest
from ..rules import has_critical_keywords

# Probara si las palabras ingresadas en las tuplas obtienen un True de acuerdo a la lista CRITICAL KEYWORDS 
# @pytest.mark.parametrize("text, expected", [("Bloqueado", True), ("No tengo audio", False),("Tenemos UNA caída total", True),("PÉRDIDA DE DATOS", True)])
# def test_has_critical_keywords_detects_critical_text(text, expected):
#     assert has_critical_keywords(text) == expected

# Usaremos la manera mas corta y facil para probar estas palabras criticas
@pytest.mark.parametrize("text", [("caída total del servicio"),("caida total"),("NO FUNCIONA NADA"),("Tuvimos pérdida de datos ayer"),("No puedo acceder a mi cuenta"),("Mi usuario quedó bloqueado"),("Hay un problema de seguridad"),("Tenemos UNA caída total")])
def test_has_critical_keywords_detects_critical_text(text):
    assert has_critical_keywords(text) is True

# # Probara si las palabras ingresadas como text existen en la lista CRITICAL KEYWORDS  
# @pytest.mark.parametrize("text, expected", [("En espera", False), ("Es la tercera vez", False),("Tenemos UNA caída total", True),("PÉRDIDA DE DATOS", True),("Temblor",False),("",False),(None,False)])
# def test_has_critical_keywords_ignores_normal_text(text, expected):
#     assert has_critical_keywords(text) == expected

@pytest.mark.parametrize("text", [("En espera"),("Es la tercera vez"),("Temblor"),(""),(None),("Desbloqueado")])
def test_has_critical_keywords_ignores_normal_text(text):
    assert has_critical_keywords(text) is False
    
    
@pytest.mark.parametrize("text", [("Ya esta desbloqueado")])   
def test_has_critical_keywords_does_not_match_inside_other_words(text):
    assert has_critical_keywords(text) is False
    
@pytest.mark.parametrize("text", [("No hay caída total"),("No hubo pérdida de datos"),("Sin pérdida de datos"),("No está bloqueado"),("No ha sido bloqueado")])   
def test_has_critical_keywords_ignores_negated_phrases(text):
    assert has_critical_keywords(text) is False
# 4 test pasan excepto el de "No ha sido bloqueado" (True) porque esta negacion no esta contemplada
# en nuestras expresiones, no tenemos la expresion "no ha sido..." restringida.