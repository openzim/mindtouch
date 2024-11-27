import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/:pathMatch(.*)',
      name: 'home',
      component: HomeView
    }
  ],
  scrollBehavior(to) {
    if (to.query.anchor && typeof to.query.anchor === 'string') {
      return // HomeView will handle the scroll to the anchor
    }
    return { top: 0, behavior: 'smooth' }
  }
})

export default router
