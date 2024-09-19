import pytest
import time
from app.parsing import ParserKomTrans


class TestParserKomTrans:
    # https://www.comtt.ru/
    parser = ParserKomTrans()

    @pytest.mark.parametrize("art, prod, reference",
                             [("AZ9925520250", "HOWO", [])])
    def test_parsing_article_costs_1(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("1802905005830", "ROSTAR", [5365.02])])
    def test_parsing_article_costs_2(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("30219", "BRINGER LIGHT", [])])
    def test_parsing_article_costs_3(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("'30219", "BRINGER LIGHT", [])])
    def test_parsing_article_costs_dirty_input(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("535160", "ELRING", [0, 5])])
    def test_parsing_article_delivery_days(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_days = parsing_result["delivery_days"]
        assert parsed_days == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("", "", ([], []))])
    def test_parsing_article_check_synonyms(self, art, prod, reference):
        time.sleep(3)
        pass
