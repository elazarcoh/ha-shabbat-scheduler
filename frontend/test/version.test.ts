import { describe, expect, it } from 'vitest';
import { CARD_VERSION } from '../src/version';

describe('CARD_VERSION', () => {
  it('is a semver string the resource URL can be stamped with', () => {
    expect(CARD_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
  });
});
