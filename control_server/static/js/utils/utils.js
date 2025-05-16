function renderTemplate(templateElement, data) {
  const tempDiv = document.createElement('div');
  tempDiv.appendChild(templateElement.content.cloneNode(true));
  let html = tempDiv.innerHTML;

  html = html.replace(/\[\[\s*if\s+(\w+)\s*\]\]([\s\S]*?)\[\[\s*endif\s*\]\]/g, (match, key, content) => {
    return data[key] ? content : '';
  });

  html = html.replace(/\[\[\s*(\w+)\s*\]\]/g, (match, key) => {
    return data[key] ?? '';
  });

  return html;
}