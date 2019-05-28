from abc import ABCMeta, abstractmethod


class AbstractPreprocessor(metaclass=ABCMeta):

    @abstractmethod
    def preprocess(self, text):
        pass
