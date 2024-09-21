import pytest
import time
from app.parsing import ParserKomTrans, ParserTrackMotors


# TODO: после добавления в парсеры работы с синонимами,  доработать test_parsing_article_check_synonyms

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


class TestParserTrackMotors:
    # https://market.tmtr.ru
    parser = ParserTrackMotors()

    @pytest.mark.parametrize("art, prod, reference",
                             [("AZ9925520250", "HOWO", [1272.0])])
    def test_parsing_article_costs_1(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        print(parsing_result)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("1802905005830", "ROSTAR", [4451.0, 7675.0])])
    def test_parsing_article_costs_2(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("30219", "BRINGER LIGHT", [739.0])])
    def test_parsing_article_costs_3(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("'30219", "BRINGER LIGHT", [739.0])])
    def test_parsing_article_costs_dirty_input(self, art, prod, reference):
        time.sleep(3)
        parsing_result = self.parser.parsing_article(art, prod)
        parsed_costs = parsing_result["costs"]
        assert parsed_costs == reference

    @pytest.mark.parametrize("art, prod, reference",
                             [("535160", "ELRING", [3, 68])])
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
