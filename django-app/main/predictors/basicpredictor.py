from .abstractpredictor import AbstractPredictor


class BasicPredictor(AbstractPredictor):

    def predict_hour(self):
        pass

    def predict_day(self):
        pass

    def predict_week(self):
        pass

    def predict_month(self):
        pass

    def evaluate_trend(self):
        pass

    def evaluate_sentiment(self):
        pass

    def _load_date(self, dbinst):
        pass
