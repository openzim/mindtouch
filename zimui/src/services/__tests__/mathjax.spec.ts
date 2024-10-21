import { describe, it, expect } from 'vitest'
import mathjaxService from '../mathjax'

describe('MathJaxService', () => {
  it('computes front 1.2. properly', () => {
    expect(mathjaxService.frontFromTitle('1.2: The Scientific Method')).toBe('1.2.')
  })
  it('computes front 1.3. properly', () => {
    expect(mathjaxService.frontFromTitle('1.3: The Foo Method')).toBe('1.3.')
  })
  it('computes front 1. properly', () => {
    expect(mathjaxService.frontFromTitle('1: The Title Method')).toBe('1.')
  })
})
