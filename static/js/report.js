/* Preview controls never enter the submitted document. */
document.addEventListener('DOMContentLoaded', () => {
  const fields = [...document.querySelectorAll('[data-report-meta-input]')];
  const status = document.getElementById('metadata-status');
  const sync = () => {
    fields.forEach(input => document.querySelectorAll(`[data-report-meta="${input.dataset.reportMetaInput}"]`).forEach(node => {
      node.textContent = input.value;
      node.classList.toggle('empty-metadata', !input.value.trim());
    }));
    const missing = fields.filter(input => !input.value.trim()).map(input => input.dataset.label);
    if (status) status.textContent = missing.length ? `Przed oddaniem uzupełnij: ${missing.join(', ').toLowerCase()}.` : 'Dane na stronie tytułowej są uzupełnione.';
  };
  fields.forEach(input => input.addEventListener('input', sync));
  sync();
  document.getElementById('print-report')?.addEventListener('click', async () => {
    await document.fonts.ready;
    window.print();
  });
});
