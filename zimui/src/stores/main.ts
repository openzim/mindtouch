import { defineStore } from 'pinia'
import axios, { AxiosError } from 'axios'
import type { Shared } from '@/types/shared'

export type RootState = {
  shared: Shared | null
  isLoading: boolean
  errorMessage: string
  errorDetails: string
}

export const useMainStore = defineStore('main', {
  state: () =>
    ({
      shared: null,
      isLoading: false,
      errorMessage: '',
      errorDetails: ''
    }) as RootState,
  getters: {},
  actions: {
    async fetchShared() {
      this.isLoading = true
      this.errorMessage = ''
      this.errorDetails = ''

      return axios.get('./content/shared.json').then(
        (response) => {
          this.isLoading = false
          this.shared = response.data as Shared
        },
        (error) => {
          this.isLoading = false
          this.shared = null
          this.errorMessage = 'Failed to load shared data.'
          if (error instanceof AxiosError) {
            this.handleAxiosError(error)
          }
        }
      )
    },
    checkResponseObject(response: unknown, msg: string = '') {
      if (response === null || typeof response !== 'object') {
        if (msg !== '') {
          this.errorDetails = msg
        }
        throw new Error('Invalid response object.')
      }
    },
    handleAxiosError(error: AxiosError<object>) {
      if (axios.isAxiosError(error) && error.response) {
        const status = error.response.status
        switch (status) {
          case 400:
            this.errorDetails =
              'HTTP 400: Bad Request. The server could not understand the request.'
            break
          case 404:
            this.errorDetails =
              'HTTP 404: Not Found. The requested resource could not be found on the server.'
            break
          case 500:
            this.errorDetails =
              'HTTP 500: Internal Server Error. The server encountered an unexpected error.'
            break
        }
      }
    },
    setErrorMessage(message: string) {
      this.errorMessage = message
    }
  }
})
