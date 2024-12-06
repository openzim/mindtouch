<script setup lang="ts">
import { watch, ref, nextTick } from 'vue'

import { useMainStore } from '@/stores/main'
import { useRoute } from 'vue-router'
import type { SharedPage } from '@/types/shared'

const main = useMainStore()

const route = useRoute()

const getPage = function () {
  if (main.shared === null) {
    return null
  }
  let path = route.params.pathMatch
  if (Array.isArray(path)) {
    if (path.length != 1) {
      console.error('Improper path length: ' + path)
      return null
    }
    path = path[0]
  }
  if (path == '') {
    path = main.shared.rootPagePath
  }
  const page = main.pagesByPath[path] || null
  if (page) {
    main.fetchPageContent(page)
  }
  return page
}

const page = ref<SharedPage | null>(getPage())

watch(
  () => (main.shared ? route.params.pathMatch : undefined),
  () => {
    page.value = getPage()
    if (page.value) {
      document.title = page.value.title
    }
  }
)

// Scroll to anchor when present (cannot be done in router, page is not yet loaded)
watch(
  // We need to watch htmlBody to be sure that body is loaded, and route.query.anchor
  // to know when anchor is present
  () => (main.pageContent?.htmlBody || '') + route.query.anchor,
  async () => {
    await nextTick()
    if (typeof route.query.anchor !== 'string') {
      return
    }
    const anchors = document.querySelectorAll(`a[name="${route.query.anchor}"]`)
    if (anchors && anchors.length > 0) {
      return anchors[0].scrollIntoView()
    }
  }
)
</script>

<template>
  <!-- Reproduce DOM structure of libretexts.org for proper CSS functioning -->
  <main class="elm-skin-container">
    <article id="elm-main-content" class="elm-content-container">
      <h1>{{ page?.title }}</h1>
      <section
        class="mt-content-container"
        v-if="main.pageContent"
        v-html="main.pageContent.htmlBody"
      ></section>
      <div v-else>Page not found</div>
    </article>
  </main>
</template>
