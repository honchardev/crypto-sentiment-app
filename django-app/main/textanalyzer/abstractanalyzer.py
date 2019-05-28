from abc import ABCMeta, abstractmethod


class AbstractAnalyzer(metaclass=ABCMeta):
    
    @abstractmethod
    def analyze(self, text_content):
        pass
