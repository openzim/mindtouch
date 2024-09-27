import { describe, it, expect } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import ErrorDisplay from '../ErrorDisplay.vue'
import { useMainStore } from '@/stores/main'
import { vi } from 'vitest'
const vuetify = createVuetify({
  components,
  directives
})

describe('ErrorDisplay', () => {
  it('renders properly', () => {
    const pinia = createTestingPinia({
      createSpy: vi.fn
    })
    const main = useMainStore()
    const errorMessage = "I've got an error"
    main.errorMessage = errorMessage
    const wrapper = mount(ErrorDisplay, {
      global: {
        plugins: [pinia, vuetify]
      }
    })
    expect(wrapper.text()).toContain('Something went wrong')
    expect(wrapper.text()).toContain('Go back home')
  })
})
