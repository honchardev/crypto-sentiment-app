from abc import ABCMeta, abstractmethod


class AbstractScraper(metaclass=ABCMeta):

    @abstractmethod
    def scrape(self, from_datetime, to_datetime):
        pass

    @abstractmethod
    def scrape_single(self, link):
        pass

