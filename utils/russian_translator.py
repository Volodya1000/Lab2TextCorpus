from typing import Dict, List

class RussianTranslator:
    def __init__(self):
        self.morph_translations = {
            "Case": {
                "Nom": "Именительный падеж",
                "Gen": "Родительный падеж",
                "Dat": "Дательный падеж",
                "Acc": "Винительный падеж",
                "Ins": "Творительный падеж",
                "Loc": "Предложный падеж"
            },
            "Number": {
                "Sing": "Единственное число",
                "Plur": "Множественное число"
            },
            "Gender": {
                "Masc": "Мужской род",
                "Fem": "Женский род",
                "Neut": "Средний род"
            },
            "Tense": {
                "Past": "Прошедшее время",
                "Pres": "Настоящее время",
                "Fut": "Будущее время"
            },
            "Aspect": {
                "Imp": "Несовершенный вид",
                "Perf": "Совершенный вид"
            },
            "Mood": {
                "Ind": "Изъявительное наклонение",
                "Imp": "Повелительное наклонение"
            },
            "VerbForm": {
                "Fin": "Личная форма",
                "Inf": "Инфинитив",
                "Part": "Причастие",
                "Ger": "Деепричастие"
            },
            "Person": {
                "1": "1-е лицо",
                "2": "2-е лицо",
                "3": "3-е лицо"
            },
            "Animacy": {
                "Anim": "Одушевленный",
                "Inan": "Неодушевленный"
            },
            "Voice": {
                "Act": "Действительный залог",
                "Pass": "Страдательный залог",
                "Mid": "Средний залог"
            },
            "Degree": {
                "Pos": "Положительная степень",
                "Cmp": "Сравнительная степень",
                "Sup": "Превосходная степень"
            },
            "Polarity": {
                "Neg": "Отрицательная полярность"
            }
        }
        # обратный словарь: «Русский» → код
        self.reverse_morph: Dict[str, str] = {
            rus: code
            for feat_map in self.morph_translations.values()
            for code, rus in feat_map.items()
        }

        self.pos_translations = {
            "NOUN": "Существительное",
            "VERB": "Глагол",
            "ADJ": "Прилагательное",
            "ADV": "Наречие",
            "PRON": "Местоимение",
            "NUM": "Числительное",
            "ADP": "Предлог",
            "CONJ": "Союз",
            "PART": "Частица",
            "INTJ": "Междометие"
        }

    def translate_morph(self, morph_info: Dict[str, str]) -> Dict[str, str]:
        translated = {}
        for key, value in morph_info.items():
            translated[key] = self.morph_translations.get(key, {}).get(value, value)
        return translated

    def translate_syntax(self, syntax_role: str) -> str:
        # ... как было раньше ...
        return syntax_role

    def get_all_features(self) -> List[str]:
        return list(self.morph_translations.keys())

    def get_feature_values(self, feature: str) -> List[str]:
        return list(self.morph_translations.get(feature, {}).values())

    def translate_pos(self, pos: str) -> str:
        return self.pos_translations.get(pos, pos)

    def translate_filter_display(self, feature: str, rus_value: str) -> str:
        """
        По выбору пользователя (rus_value) возвращает внутренний код (Past, Nom и т.д.)
        """
        return self.reverse_morph.get(rus_value, rus_value)

    def translate_syntax(self, syntax_role):
        return self.syntax_translations.get(syntax_role, syntax_role)
    
   