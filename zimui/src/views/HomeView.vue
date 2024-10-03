<script setup lang="ts">
import { onMounted } from 'vue'

import { useHomeStore } from '@/stores/home'

// Fetch the home data
const home = useHomeStore()
onMounted(async () => {
  try {
    await home.fetchHome()
  } catch (error) {
    home.setErrorMessage('An unexpected error occured.')
  }
})
</script>

<template>
  <v-container>
    <p v-for="paragraph in home.home?.welcomeTextParagraphs" :key="paragraph">{{ paragraph }}</p>
  </v-container>
</template>
