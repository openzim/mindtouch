describe('Home of the ZIM UI', () => {
  beforeEach(() => {
    cy.intercept('GET', '/content/home.json', { fixture: 'home.json' }).as('getHome')
    cy.intercept('GET', '/content/shared.json', { fixture: 'shared.json' }).as('getShared')
    cy.intercept('GET', '/content/config.json', { fixture: 'config.json' }).as('getConfig')
    cy.visit('/')
    cy.wait('@getHome')
    cy.wait('@getShared')
    cy.wait('@getConfig')
  })

  it('loads the proper header image', () => {
    cy.get('div[class="header-bar"]')
      .find('img')
      .should('be.visible')
      .should('have.attr', 'src', 'content/logo.png')
  })

  it('loads the first paragraph only once', () => {
    cy.contains('p', 'Paragraph 2').should('be.visible')
    cy.get('p:contains("Paragraph 2")').should('have.length', 1)
  })

  it('loads the second paragraph only once', () => {
    cy.contains('p', 'Paragraph 2').should('be.visible')
    cy.get('p:contains("Paragraph 2")').should('have.length', 1)
  })
})
