import { defineStore } from 'pinia'
import axios, { AxiosError } from 'axios'
import type { Home } from '@/types/home'
import { useMainStore } from './main'

export type RootState = {
  home: Home | null
}

export const useHomeStore = defineStore('home', {
  state: () =>
    ({
      home: null
    }) as RootState,
  getters: {},
  actions: {
    async fetchHome() {
      const main = useMainStore()
      main.isLoading = true
      main.errorMessage = ''
      main.errorDetails = ''

      return axios.get('./content/home.json').then(
        (response) => {
          main.isLoading = false
          this.home = response.data as Home
        },
        (error) => {
          main.isLoading = false
          this.home = null
          main.errorMessage = 'Failed to load home data.'
          if (error instanceof AxiosError) {
            main.handleAxiosError(error)
          }
        }
      )
    },
    setErrorMessage(message: string) {
      const main = useMainStore()
      main.errorMessage = message
    }
  }
})
