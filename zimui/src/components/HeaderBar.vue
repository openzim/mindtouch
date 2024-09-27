<script setup lang="ts">
import { onMounted } from 'vue'

import { useMainStore } from '@/stores/main'

import logoPlaceholder from '@/assets/logo-placeholder.png'

// Fetch the home data
const main = useMainStore()
onMounted(async () => {
  try {
    await main.fetchShared()
  } catch (error) {
    main.setErrorMessage('An unexpected error occured.')
  }
})
</script>

<template>
  <div class="header-bar">
    <v-img
      :lazy-src="logoPlaceholder"
      :src="main.shared?.logoPath"
      alt="LibreTexts logo"
      class="logo"
      width="auto"
      height="70"
    />
  </div>
</template>

<style scoped>
.header-bar {
  padding: 0.25rem;
}
</style>
