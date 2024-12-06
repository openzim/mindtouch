import { describe, it, expect } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import HeaderBar from '../HeaderBar.vue'
import { useMainStore } from '@/stores/main'
import { vi } from 'vitest'
const vuetify = createVuetify({
  components,
  directives
})

describe('HeaderBar', () => {
  it('renders properly with default placeholder', () => {
    const pinia = createTestingPinia({
      createSpy: vi.fn
    })
    const wrapper = mount(HeaderBar, {
      global: {
        plugins: [pinia, vuetify]
      }
    })
    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('/src/assets/logo-placeholder.png')
  })
  it('renders properly with shared data', () => {
    const pinia = createTestingPinia({
      createSpy: vi.fn
    })
    const main = useMainStore()
    const logoPath = 'content/logo.png'
    main.shared = { logoPath: logoPath, rootPagePath: '', libraryOnlineUrl: '', pages: [] }

    const wrapper = mount(HeaderBar, {
      global: {
        plugins: [pinia, vuetify]
      }
    })
    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe(logoPath)
  })
})
