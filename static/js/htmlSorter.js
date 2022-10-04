// sort column based on HTML values
// ref: https://github.com/wenzhixin/bootstrap-table/issues/461
export function htmlSorter (a, b) {
  const atext = $(a).text()
  const btext = $(b).text()
  if (atext < btext) return -1
  if (atext > btext) return 1
  return 0
}
