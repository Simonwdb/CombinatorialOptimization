from Solution import Solution

def write_solution(solution: Solution, instance, filename: str):
    """
    Writes a Solution object to a text file in the VeRoLog solution format.
    Only writes the minimal required information (no extra data).
    The extra data (cost, distances, depot info) can be added by running Validate.py.
    """
    with open(filename, 'w') as f:
        # Write header
        f.write(f'DATASET = {instance.Dataset}\n')
        f.write(f'NAME = {instance.Name}\n')
        f.write('\n')
        
        # Write days
        for day in solution.days:
            f.write(f'DAY = {day.day_number}\n')
            f.write(f'NUMBER_OF_VEHICLES = {len(day.routes)}\n')
            
            # Write routes
            for i, route in enumerate(day.routes):
                stops = '\t'.join(str(s) for s in route.stops)
                f.write(f'{i+1}\tR\t{stops}\n')
            
            f.write('\n')