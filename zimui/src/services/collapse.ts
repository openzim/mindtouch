/*
Service to handle DOM manipulation to collapse subpages of books when there are too many

See e.g. https://geo.libretexts.org/Courses/Fullerton_College (page ID 32303)
*/

const maxVisibleItems = 5

class CollapseService {
  handle_page_load() {
    // Remove show all buttons which migth have been added previously
    const previousShowAllButtons = document.querySelectorAll('button.zim-show-all-button')
    for (const previousShowAllButton of previousShowAllButtons) {
      previousShowAllButton.remove()
    }

    // Load all ul elements corresponding to a category (e.g. books)
    const ulElements = document.querySelectorAll(
      'div.mt-category-container dd.mt-listing-detailed-subpages ul'
    )

    for (const ulElement of ulElements) {
      if (!ulElement.parentNode) {
        continue // Failsafe, just in case
      }
      const listItems = ulElement.querySelectorAll('li')

      // Check if there are more than 5 items
      if (listItems.length <= maxVisibleItems) {
        return
      }

      // Hide all list items after the 5th one
      listItems.forEach((item, index) => {
        if (index >= maxVisibleItems) {
          item.style.display = 'none'
        }
      })

      // Create the "Show all" button
      const showAllButton = document.createElement('button')
      showAllButton.className =
        'mt-icon-expand-collapse mt-reveal-listing-expand-link zim-show-all-button'
      showAllButton.title = 'Show all'

      // Insert the button after the <ul> element
      ulElement.parentNode.insertBefore(showAllButton, ulElement.nextSibling)

      // Toggle visibility and text on button click
      let isExpanded = false
      showAllButton.addEventListener('click', function () {
        isExpanded = !isExpanded
        listItems.forEach((item, index) => {
          item.style.display = isExpanded || index < maxVisibleItems ? '' : 'none'
        })
        showAllButton.title = isExpanded ? 'Show less' : 'Show all'
      })
    }
  }
}

const collapseService = new CollapseService()
Object.freeze(collapseService)

export default collapseService
