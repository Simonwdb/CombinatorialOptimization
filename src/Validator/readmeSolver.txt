# VeRoLog Solver - GreedySolver

This README explains how to use the `GreedySolver` to generate an initial feasible solution for the VeRoLog Solver Challenge instances.

---

## Project Structure

Make sure the following files are in the same directory:

```
├── baseCVRPTWUI.py          # Base parser (provided)
├── InstanceCVRPTWUI.py      # Instance parser (provided)
├── Validate.py              # Solution validator (provided)
├── BaseSolver.py            # Abstract base class for solvers
├── GreedySolver.py          # Greedy solver implementation
├── FeasibleGreedySolver.py  # Feasible greedy solver implementation
├── Solution.py              # Solution data classes
├── Writer.py                # Solution writer
└── your_instance.txt        # Your instance file
```

---

## What is the GreedySolver?

The `GreedySolver` is the simplest possible solver. It uses a **pure greedy strategy**:

- Deliver each request on the **earliest possible day** (`fromDay`)
- Pick up each request on the **fixed pickup day** (`fromDay + numDays`)
- Each job gets its **own route** (no combining of jobs)

> ⚠️ The `GreedySolver` does **not** check tool availability constraints. It may produce an infeasible solution. Use the `FeasibleGreedySolver` for a guaranteed feasible solution.

---

## Step-by-step usage in a Notebook

### Step 1: Import dependencies

```python
from pathlib import Path
from InstanceCVRPTWUI import InstanceCVRPTWUI
from GreedySolver import GreedySolver
from FeasibleGreedySolver import FeasibleGreedySolver
from Writer import write_solution
```

---

### Step 2: Load the instance

```python
# Set the path to your instance file
instance_file = Path('your_instance.txt')

# Load and parse the instance
instance = InstanceCVRPTWUI(inputfile=str(instance_file), filetype='txt')
instance.calculateDistances()

# Check if the instance is valid
if instance.isValid():
    print(f"Instance loaded: {instance.Name}")
    print(f"Days: {instance.Days}")
    print(f"Requests: {len(instance.Requests)}")
    print(f"Tools: {len(instance.Tools)}")
else:
    print("Invalid instance file!")
    print('\n'.join(instance.errorReport))
```

---

### Step 3a: Solve using GreedySolver

```python
# Create solver and generate solution
solver = GreedySolver(instance=instance)
solution = solver.solve()

print(f"Solution generated with {len(solution.days)} active days")
```

---

### Step 3b: Solve using FeasibleGreedySolver (recommended)

The `FeasibleGreedySolver` extends the `GreedySolver` by checking tool availability constraints. If a request cannot be delivered on `fromDay`, it is postponed by one day until a feasible day is found.

```python
# Create solver and generate solution
solver = FeasibleGreedySolver(instance=instance)
solution = solver.solve()

# Enable debug output to see postponed requests
solution = solver.solve(debug=True)
```

---

### Step 4: Write the solution to a file

```python
# Write solution to a text file
output_file = 'my_solution.txt'
write_solution(solution=solution, instance=instance, filename=output_file)
print(f"Solution written to: {output_file}")
```

---

### Step 5: Validate the solution

Use the provided `Validate.py` script to validate the solution. Run the following command in your terminal:

```bash
python3 Validate.py -i your_instance.txt -s my_solution.txt
```

To also write the validated solution with extra information (costs, distances, depot info):

```bash
python3 Validate.py -i your_instance.txt -s my_solution.txt -o my_solution_validated.txt -e
```

---
