<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useMainStore } from '@/stores/main'
import HeaderBar from './components/HeaderBar.vue'
import ErrorDisplay from './components/ErrorDisplay.vue'
const main = useMainStore()
</script>

<template>
  <v-app>
    <v-main>
      <div v-if="main.errorMessage">
        <error-display />
      </div>
      <div v-else>
        <header-bar />
        <router-view />
      </div>
    </v-main>
  </v-app>
</template>
