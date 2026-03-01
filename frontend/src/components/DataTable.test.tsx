/**
 * Tests for the DataTable component.
 *
 * Focus: column rendering, empty state, sorting behavior, row clicks,
 *        and selectable mode with checkboxes.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import DataTable from './DataTable'

const columns = [
  { key: 'name', header: 'Name', sortable: true },
  { key: 'score', header: 'Score' },
]

const data = [
  { id: '1', name: 'Charlie', score: 80 },
  { id: '2', name: 'Alice', score: 90 },
  { id: '3', name: 'Bob', score: 70 },
]

describe('DataTable — empty state', () => {
  it('shows the default "No data" message when data is empty', () => {
    render(<DataTable columns={columns} data={[]} />)
    expect(screen.getByText('No data')).toBeInTheDocument()
  })

  it('shows a custom empty message when provided', () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="Nothing to show" />)
    expect(screen.getByText('Nothing to show')).toBeInTheDocument()
  })
})

describe('DataTable — rendering', () => {
  it('renders all column headers', () => {
    render(<DataTable columns={columns} data={data} />)
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Score')).toBeInTheDocument()
  })

  it('renders a row for each data item', () => {
    render(<DataTable columns={columns} data={data} />)
    expect(screen.getByText('Charlie')).toBeInTheDocument()
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
  })

  it('uses the custom render function when provided', () => {
    const cols = [
      {
        key: 'name',
        header: 'Name',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        render: (row: any) => <span data-testid="custom">{String(row.name).toUpperCase()}</span>,
      },
    ]
    render(<DataTable columns={cols} data={[{ id: '1', name: 'alice' }]} />)
    expect(screen.getByTestId('custom')).toHaveTextContent('ALICE')
  })

  it('falls back to String() for cells without a render function', () => {
    render(<DataTable columns={columns} data={[{ id: '1', name: 'Test', score: 42 }]} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })
})

describe('DataTable — sorting', () => {
  // Helper: get the sortable column header th by index (0-based among sortable cols)
  function getColumnHeader(name: string) {
    return screen.getByRole('columnheader', { name: new RegExp(name) })
  }

  it('sorts ascending on first click of a sortable column', () => {
    render(<DataTable columns={columns} data={data} />)
    fireEvent.click(getColumnHeader('Name'))
    const rows = screen.getAllByRole('row').slice(1) // skip header
    expect(rows[0]).toHaveTextContent('Alice')
    expect(rows[1]).toHaveTextContent('Bob')
    expect(rows[2]).toHaveTextContent('Charlie')
  })

  it('sorts descending on second click of the same column', () => {
    render(<DataTable columns={columns} data={data} />)
    fireEvent.click(getColumnHeader('Name'))
    fireEvent.click(getColumnHeader('Name'))
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0]).toHaveTextContent('Charlie')
    expect(rows[2]).toHaveTextContent('Alice')
  })

  it('shows ↑ indicator when sorted ascending', () => {
    render(<DataTable columns={columns} data={data} />)
    fireEvent.click(getColumnHeader('Name'))
    expect(getColumnHeader('Name')).toHaveTextContent('↑')
  })

  it('shows ↓ indicator when sorted descending', () => {
    render(<DataTable columns={columns} data={data} />)
    fireEvent.click(getColumnHeader('Name'))
    fireEvent.click(getColumnHeader('Name'))
    expect(getColumnHeader('Name')).toHaveTextContent('↓')
  })

  it('does not sort when a non-sortable column header is clicked', () => {
    render(<DataTable columns={columns} data={data} />)
    fireEvent.click(getColumnHeader('Score'))
    // Order should be unchanged: Charlie, Alice, Bob
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0]).toHaveTextContent('Charlie')
  })

  it('resets to ascending when a different column is clicked', () => {
    const cols = [
      { key: 'name', header: 'Name', sortable: true },
      { key: 'city', header: 'City', sortable: true },
    ]
    const rows = [
      { id: '1', name: 'Bob', city: 'Zagreb' },
      { id: '2', name: 'Alice', city: 'Amsterdam' },
    ]
    render(<DataTable columns={cols} data={rows} />)
    // Sort by name descending
    fireEvent.click(getColumnHeader('Name'))
    fireEvent.click(getColumnHeader('Name'))
    // Now click City — should reset to ascending
    fireEvent.click(getColumnHeader('City'))
    expect(getColumnHeader('City')).toHaveTextContent('↑')
  })
})

describe('DataTable — row click', () => {
  it('calls onRowClick with the row data when a row is clicked', () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={columns} data={data} onRowClick={onRowClick} />)
    fireEvent.click(screen.getByText('Alice'))
    expect(onRowClick).toHaveBeenCalledWith(data[1])
  })

  it('adds cursor-pointer class to rows when onRowClick is provided', () => {
    render(<DataTable columns={columns} data={data} onRowClick={() => {}} />)
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].className).toContain('cursor-pointer')
  })

  it('does not add cursor-pointer when onRowClick is absent', () => {
    render(<DataTable columns={columns} data={data} />)
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].className).not.toContain('cursor-pointer')
  })
})

describe('DataTable — selectable mode', () => {
  it('renders checkboxes for header and every row', () => {
    render(
      <DataTable
        columns={columns}
        data={data}
        selectable
        selectedIds={new Set()}
        onSelectionChange={() => {}}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox')
    // 1 header checkbox + 3 row checkboxes
    expect(checkboxes).toHaveLength(4)
  })

  it('marks rows in selectedIds as checked', () => {
    render(
      <DataTable
        columns={columns}
        data={data}
        selectable
        selectedIds={new Set(['2'])}
        onSelectionChange={() => {}}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[]
    // checkboxes[0] = header, checkboxes[1..3] = rows ordered Charlie, Alice, Bob
    expect(checkboxes[2].checked).toBe(true)  // Alice = id '2'
    expect(checkboxes[1].checked).toBe(false) // Charlie
    expect(checkboxes[3].checked).toBe(false) // Bob
  })

  it('calls onSelectionChange with all IDs when select-all is clicked', () => {
    const onChange = vi.fn()
    render(
      <DataTable
        columns={columns}
        data={data}
        selectable
        selectedIds={new Set()}
        onSelectionChange={onChange}
      />,
    )
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    const arg: Set<string> = onChange.mock.calls[0][0]
    expect(arg).toEqual(new Set(['1', '2', '3']))
  })

  it('calls onSelectionChange with empty set when deselect-all is clicked', () => {
    const onChange = vi.fn()
    render(
      <DataTable
        columns={columns}
        data={data}
        selectable
        selectedIds={new Set(['1', '2', '3'])}
        onSelectionChange={onChange}
      />,
    )
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    const arg: Set<string> = onChange.mock.calls[0][0]
    expect(arg).toEqual(new Set())
  })

  it('toggles a single row on row checkbox click', () => {
    const onChange = vi.fn()
    render(
      <DataTable
        columns={columns}
        data={data}
        selectable
        selectedIds={new Set()}
        onSelectionChange={onChange}
      />,
    )
    // Row checkboxes start at index 1; first row is Charlie (id '1')
    fireEvent.click(screen.getAllByRole('checkbox')[1])
    const arg: Set<string> = onChange.mock.calls[0][0]
    expect(arg.has('1')).toBe(true)
  })

  it('deselects a row when it is already selected', () => {
    const onChange = vi.fn()
    render(
      <DataTable
        columns={columns}
        data={data}
        selectable
        selectedIds={new Set(['1'])}
        onSelectionChange={onChange}
      />,
    )
    fireEvent.click(screen.getAllByRole('checkbox')[1]) // Charlie row
    const arg: Set<string> = onChange.mock.calls[0][0]
    expect(arg.has('1')).toBe(false)
  })
})
