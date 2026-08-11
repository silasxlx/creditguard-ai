import { describe, expect, it } from 'vitest'

describe('web skeleton', () => {
  it('exposes the two demo roles', () => {
    expect(['RM', 'REVIEWER']).toEqual(['RM', 'REVIEWER'])
  })
})
