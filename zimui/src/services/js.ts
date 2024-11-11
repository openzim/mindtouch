/*
Service to handle DOM manipulation to add/remove additional JS scripts for mindtouch
*/

class JsService {
  addScript(path: string) {
    const script = document.createElement('script', {
      id: 'mathjax-script'
    } as ElementCreationOptions)
    script.src = path
    document.head.appendChild(script)
  }
}

const jsService = new JsService()
Object.freeze(jsService)

export default jsService
