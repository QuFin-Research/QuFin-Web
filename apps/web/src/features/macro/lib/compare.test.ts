import { describe, expect, it } from 'vitest';
import { compareScale, moveTone, rankLabel, sparkPath, writeValue } from './compare';

describe('compare helpers', () => {
  it('scales bars against the largest usable value', () => {
    const scale = compareScale([2, 4, 1]);
    expect(scale(4)).toBe(1);
    expect(scale(2)).toBe(0.5);
    expect(scale(-1)).toBe(0);
    expect(compareScale([])(3)).toBe(0);
  });

  it('ranks usable rows only', () => {
    expect(rankLabel(0, true)).toBe('1');
    expect(rankLabel(5, false)).toBe('—');
  });

  it('colours a rise as worse when higher is worse', () => {
    expect(moveTone(0.4, 'worse')).toBe('text-bear');
    expect(moveTone(-0.4, 'worse')).toBe('text-bull');
    expect(moveTone(-0.4, 'better')).toBe('text-bear');
    expect(moveTone(0, 'worse')).toBe('text-muted-foreground');
  });

  it('writes a value with its unit', () => {
    expect(writeValue(3.72, '%')).toBe('3.7%');
    expect(writeValue(4, '%')).toBe('4.0%');
  });

  it('draws a path from two points and none from fewer', () => {
    expect(sparkPath([1], 96, 24)).toBeNull();
    const path = sparkPath([1, 2, 3], 96, 24);
    expect(path?.startsWith('M0.0,')).toBe(true);
    expect(path?.split('L')).toHaveLength(3);
    expect(sparkPath([5, 5, 5], 96, 24)).not.toBeNull(); // a flat line must not divide by zero
  });
});
