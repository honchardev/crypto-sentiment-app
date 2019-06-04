from abc import ABCMeta, abstractmethod


class AbstractPredictor(metaclass=ABCMeta):

    @abstractmethod
    def predict_hour(self):
        pass

    @abstractmethod
    def predict_day(self):
        pass

    @abstractmethod
    def predict_week(self):
        pass

    @abstractmethod
    def predict_month(self):
        pass

    @abstractmethod
    def evaluate_trend(self):
        pass

    @abstractmethod
    def evaluate_sentiment(self):
        pass

    @abstractmethod
    def _load_date(self, dbinst):
        pass
