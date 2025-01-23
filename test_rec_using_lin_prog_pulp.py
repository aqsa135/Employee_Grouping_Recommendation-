# -*- coding: utf-8 -*-
"""Test_Rec_Using_Lin_Prog_Pulp.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1KrQWL1AxiKi3-MIduQlnBPQbx7QsZNv3
"""

!pip install pulp

import pandas as pd
import numpy as np
from pulp import *
import json

class GroupAssignmentOptimizer:
    def __init__(self, data_path: str, group_capacity: int = 25):
       #        Initialize the optimizer with data and constraints

        self.df = pd.read_csv(data_path)
        self.group_capacity = group_capacity
        self.groups = sorted(self.df['1th choice'].unique())
        self.employees = list(range(len(self.df)))

        # Create preference scores
        self.preference_scores = pd.DataFrame(index=self.employees, columns=self.groups)
        choice_weights = {'1th choice': 4, '2th choice': 3, '3th choice': 2, '4th choice': 1}

        for i in self.employees:
            for group in self.groups:
                score = 0
                for choice, weight in choice_weights.items():
                    if self.df.iloc[i][choice] == group:
                        score = weight
                        break
                self.preference_scores.loc[i, group] = score

    def create_optimization_model(self):
        #Create and return the PuLP optimization model with all constraints

        prob = LpProblem("Group_Assignment_Optimization", LpMaximize)

        # Decision Variables: x[i,j] = 1 if employee i is assigned to group j
        x = LpVariable.dicts("assign",
                           ((i, j) for i in self.employees for j in self.groups),
                           cat='Binary')

        # Objective: Maximize preference
        prob += lpSum(self.preference_scores.iloc[i][j] * x[i,j]
                     for i in self.employees for j in self.groups)

        # Constraint#1: Each employee must be assigned to exactly one group
        for i in self.employees:
            prob += lpSum(x[i,j] for j in self.groups) == 1

        # Constraint#2: Each group must not exceed capacity
        for j in self.groups:
            prob += lpSum(x[i,j] for i in self.employees) <= self.group_capacity

        # Constraint#3: Each section must have at least one person in each group
        sections = self.df['Section'].unique()
        for j in self.groups:
            for section in sections:
                section_employees = self.df[self.df['Section'] == section].index
                prob += lpSum(x[i,j] for i in section_employees) >= 1

        # Constraint#4: Try to balance gender distribution
        genders = self.df['Gender'].unique()
        for j in self.groups:
            for gender in genders:
                gender_employees = self.df[self.df['Gender'] == gender].index
                total_gender = len(gender_employees)
                min_per_group = (total_gender // len(self.groups)) - 1  # Allow some flexibility
                prob += lpSum(x[i,j] for i in gender_employees) >= min_per_group

        # Constraint#5: Try to balance race distribution
        races = self.df['Race'].unique()
        for j in self.groups:
            for race in races:
                race_employees = self.df[self.df['Race'] == race].index
                total_race = len(race_employees)
                min_per_group = (total_race // len(self.groups)) - 1  # Allow some flexibility
                prob += lpSum(x[i,j] for i in race_employees) >= min_per_group

        return prob, x

    def solve_and_get_assignments(self):
       # to solve optimization problem by using prob.solve and return the assignments
        prob, x = self.create_optimization_model()


        prob.solve()

        if LpStatus[prob.status] != 'Optimal':
            raise Exception(f"Could not find optimal solution. Status: {LpStatus[prob.status]}")

        # Loop to create assignment results
        assignments = []
        for i in self.employees:
            for j in self.groups:
                if value(x[i,j]) == 1:
                    original_choice = None
                    for idx, col in enumerate(['1th choice', '2th choice', '3th choice', '4th choice']):
                        if self.df.iloc[i][col] == j:
                            original_choice = idx + 1
                            break

                    assignments.append({
                        'Person': self.df.iloc[i]['Person'],
                        'Assigned_Group': j,
                        'Preference_Score': self.preference_scores.iloc[i][j],
                        'Original_Choice': original_choice,
                        'Section': self.df.iloc[i]['Section'],
                        'Gender': self.df.iloc[i]['Gender'],
                        'Race': self.df.iloc[i]['Race']
                    })

        return pd.DataFrame(assignments)

    def get_assignment_statistics(self, assignments):
        # calculate the stats
        stats = {
            'total_assigned': len(assignments),
            'average_preference_score': assignments['Preference_Score'].mean(),
            'choice_distribution': assignments['Original_Choice'].value_counts().to_dict(),
            'group_sizes': assignments['Assigned_Group'].value_counts().to_dict(),
            'section_distribution': {
                group: assignments[assignments['Assigned_Group'] == group]['Section'].value_counts().to_dict()
                for group in self.groups
            },
            'gender_distribution': {
                group: assignments[assignments['Assigned_Group'] == group]['Gender'].value_counts().to_dict()
                for group in self.groups
            },
            'race_distribution': {
                group: assignments[assignments['Assigned_Group'] == group]['Race'].value_counts().to_dict()
                for group in self.groups
            }
        }
        return stats

if __name__ == "__main__":

    optimizer = GroupAssignmentOptimizer("R4E Testing Data - Copy(Sheet1) (1).csv") # Initialize optimizer and read the csv file


    assignments = optimizer.solve_and_get_assignments()

    stats = optimizer.get_assignment_statistics(assignments)

    print("\nAssignment Summary:")
    print("-" * 50)
    print(f"Total employees assigned: {stats['total_assigned']}")
    print(f"Average preference score: {stats['average_preference_score']:.2f}")

    print("\nChoice Distribution:")
    for choice, count in sorted(stats['choice_distribution'].items()):
        print(f"Got {choice}{'st' if choice == 1 else 'nd' if choice == 2 else 'rd' if choice == 3 else 'th'} choice: {count} employees")

    print("\nGroup Sizes:")
    for group, size in stats['group_sizes'].items():
        print(f"{group}: {size} employees")

    # Save results
    assignments.to_csv("optimized_group_assignments.csv", index=False)
    with open("assignment_statistics.json", "w") as f:
        json.dump(stats, f, indent=2)

    print("\nResults saved to 'optimized_group_assignments.csv' and 'assignment_statistics.json'")

