# Progressive Refinement Feature

## How It Works

### Option 1: Fresh Start (Default - Checkbox Unchecked ☐)
Each time you click "Calculate Layout", the algorithm:
1. Starts with a completely new random initial layout
2. Runs Simulated Annealing optimization from scratch
3. Returns a new, independent solution

**Use this when:**
- You want to try different random starting points
- You're exploring various layout possibilities
- You want the best result from multiple independent attempts

### Option 2: Progressive Refinement (Checkbox Checked ☑)
Each time you click "Calculate Layout", the algorithm:
1. Takes the PREVIOUS result as the starting point
2. Continues optimizing from where it left off
3. Gradually refines the existing layout

**Use this when:**
- You got a decent result but think it can improve
- You want to fine-tune an existing layout
- You want to squeeze out the last bit of optimization

## Example Workflow

### Scenario A: Finding the Best Solution
```
1. ☐ Uncheck "Use previous result as starting point"
2. Click "Calculate Layout" → Result: Area = 2,000,000
3. Click "Calculate Layout" → Result: Area = 1,850,000 (better!)
4. Click "Calculate Layout" → Result: Area = 2,200,000 (worse)
5. Click "Calculate Layout" → Result: Area = 1,750,000 (best!)
```
Each click gives you a new random attempt. Keep the best one!

### Scenario B: Refining a Good Solution
```
1. Got a layout with Area = 2,000,000
2. ☑ Check "Use previous result as starting point"
3. Click "Calculate Layout" → Result: Area = 1,900,000 (improved!)
4. Click "Calculate Layout" → Result: Area = 1,900,000 (converged)
5. Click "Calculate Layout" → Result: Area = 1,900,000 (no more improvement)
```
The algorithm gradually improves until it can't find anything better.

## Technical Details

- **Fresh Start**: Each run is independent, starting from a greedy initial placement
- **Progressive**: Uses deep copy of previous FloorPlan, then continues SA optimization
- **Temperature**: In progressive mode, SA restarts with full temperature, giving it room to explore improvements
- **Convergence**: When you see the same area multiple times in progressive mode, the solution has likely converged

## Tips

1. **Start Fresh First**: Try 3-5 fresh starts to find a good baseline
2. **Then Refine**: Check the box and click 2-3 more times to polish the result
3. **Watch the Area**: If progressive mode shows no improvement after 2-3 clicks, you've found the local optimum
4. **Reset if Stuck**: Uncheck the box and try fresh starts again if you want to explore different configurations

## Performance

- **Fresh Start**: ~5-10 seconds per run (full optimization)
- **Progressive**: ~5-10 seconds per run (continues optimization)
- **Both modes run the same number of iterations**, but progressive starts from a better position

Enjoy finding the perfect floorplan! 🎯

