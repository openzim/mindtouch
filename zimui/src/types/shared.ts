export interface SharedPage {
  id: string
  path: string
  title: string
}
export interface Shared {
  logoPath: string
  rootPagePath: string
  pages: SharedPage[]
  jsPaths: string[]
}

export interface PageContent {
  htmlBody: string
}
