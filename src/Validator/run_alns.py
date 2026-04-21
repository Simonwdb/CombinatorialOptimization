from InstanceCVRPTWUI import InstanceCVRPTWUI
from DestroyOperators import ALNSSolver
from Writer import write_solution

# Load the instance
instance_file = "testInstance.txt"  # or any other instance file
instance = InstanceCVRPTWUI(instance_file)

# Calculate distances
instance.calculateDistances()

# Check if instance is valid
if not instance.isValid():
    print("Invalid instance file")
    exit(1)

# Create and run the ALNS solver (which uses NN V2 as initial solution)
solver = ALNSSolver(instance)
solution = solver.solve()

# Write the solution
output_file = "alns_solution.txt"
write_solution(solution, instance, output_file)

print(f"ALNS solution written to {output_file}")
