import os

import numpy as py
from sklearn.linear_model import LinearRegression
from pathlib import Path


class BlackboxLinearRegression:

    def __init__(self, path: Path):
        self.path = path
        self.mean_overall_time = list()
        self.std_wall_clock_time = list()
        self.var_wall_clock_time = list()

        directory = os.fsencode(str(path))
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            with open(self.path / Path(filename), 'r') as stream:
                for line in stream:
                    line = line.strip()

                    if line.startswith("num_reports"):
                        string_split = line.split("=")
                        self.number_of_repetitions = string_split[1]
                        continue

                    if line.startswith("mean(wall_clock_time) "):
                        string_split = line.split("=")
                        self.mean_overall_time.append(string_split[1])
                        continue

                    if line.startswith("std(wall_clock_time)"):
                        string_split = line.split("=")
                        self.std_wall_clock_time.append(string_split[1])
                        continue

                    if line.startswith("variance(wall_clock_time)"):
                        string_split = line.split("=")
                        self.var_wall_clock_time.append(string_split[1])
                        continue
        self.mean_overall_time = sorted(self.mean_overall_time, key=float)

    @property
    def get_mean_overall_time(self):
        return self.mean_overall_time

    @property
    def get_std_wall_clock_time(self):
        return self.std_wall_clock_time

    @property
    def get_var_wall_clock_time(self):
        return self.var_wall_clock_time

    @property
    def get_number_of_repetitions(self):
        return self.number_of_repetitions

    @staticmethod
    def feature_linear_regression(feature_selection: list, time_results: list) -> object:

        X = py.array(feature_selection)
        y = py.array(time_results)

        return LinearRegression().fit(X, y)


if __name__ == '__main__':
    #Set Path with the folder location of the results
    test = BlackboxLinearRegression(Path("/home/aufrichtig/bachelor/xzAggregatedResults"))

    X = []
    for i in range(10):
        tmp_dic = []
        for j in range(10):
            if i == j:
                tmp_dic.append(1)
            else:
                tmp_dic.append(0)
        X.append(tmp_dic)
    for i in range(10):
        X[i][0] = 1

    linear_regression = test.feature_linear_regression(X, test.get_mean_overall_time)

    print(linear_regression.predict(py.array([[1,0,1,0,0,0,0,0,0,0]])))
    print(linear_regression.coef_)
