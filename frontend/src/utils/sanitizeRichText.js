const ALLOWED_TAGS = new Set(['B', 'STRONG', 'I', 'EM', 'U', 'BR', 'DIV', 'P'])

export const sanitizeRichText = (html = '') => {
  if (typeof DOMParser === 'undefined') return String(html).replace(/<[^>]*>/g, '')
  const documentNode = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html')
  const root = documentNode.body.firstElementChild
  root.querySelectorAll('script,style,iframe,object,embed,link,meta').forEach((node) => node.remove())
  ;[...root.querySelectorAll('*')].reverse().forEach((node) => {
    if (!ALLOWED_TAGS.has(node.tagName)) node.replaceWith(...node.childNodes)
    else [...node.attributes].forEach((attribute) => node.removeAttribute(attribute.name))
  })
  return root.innerHTML
}

export const richTextToPlainText = (html = '') => {
  if (typeof DOMParser === 'undefined') return String(html).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
  const documentNode = new DOMParser().parseFromString(sanitizeRichText(html), 'text/html')
  return (documentNode.body.textContent || '').replace(/\s+/g, ' ').trim()
}

export const plainTextToRichText = (text = '') => {
  if (typeof document === 'undefined') return String(text).replace(/[&<>]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[character]).replace(/\n/g, '<br>')
  const container = document.createElement('div')
  container.textContent = String(text)
  return container.innerHTML.replace(/\n/g, '<br>')
}
