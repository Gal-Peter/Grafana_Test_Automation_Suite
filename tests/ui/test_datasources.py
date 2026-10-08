import allure
import pytest
from playwright.sync_api import expect


@allure.epic("Grafana")
@allure.feature("Data sources")
class TestDataSources:
    @pytest.mark.smoke
    @allure.title("A created data source is listed")
    def test_datasource_listed(self, testdata_datasource, datasources_page):
        datasources_page.open()
        expect(datasources_page.datasource_link(testdata_datasource["name"])).to_be_visible()

    @pytest.mark.regression
    @allure.title("Save & test succeeds for the TestData data source")
    def test_save_and_test(self, testdata_datasource, datasources_page):
        datasources_page.open_editor(testdata_datasource["uid"])
        expect(datasources_page.save_and_test().root).to_be_visible()
