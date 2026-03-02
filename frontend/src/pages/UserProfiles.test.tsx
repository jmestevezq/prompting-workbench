import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UserProfiles from './UserProfiles'

// Mock Monaco editor — it doesn't work in jsdom
vi.mock('../components/JsonEditor', () => ({
  default: ({ value, onChange }: { value: string; onChange?: (v: string) => void }) => (
    <textarea
      data-testid="json-editor"
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
    />
  ),
}))

// Mock the API module
vi.mock('../api/client', () => ({
  api: {
    listFixtures: vi.fn().mockResolvedValue([]),
    generateProfile: vi.fn().mockResolvedValue({
      name: 'Test User',
      data: {
        ageYears: 30,
        location: { city: 'Mumbai', state: 'Maharashtra', country: 'India' },
        monthlyIncomeRange: { min: 50000, max: 80000, currency: 'INR' },
        creditScore: { score: 750, maxScore: 900 },
        bankAccounts: [{ issuerName: 'HDFC Bank' }],
        cards: [{ issuerName: 'HDFC Bank', productName: 'Regalia', cardType: 'CREDIT', cardScheme: 'VISA' }],
      },
    }),
    generateTransactions: vi.fn().mockResolvedValue({
      transactions: [{ transactionId: 'tx1', counterpartyName: 'Store', amount: 100 }],
      count: 1,
    }),
    createFixture: vi.fn().mockResolvedValue({ id: '1', name: 'Test', type: 'user_profile', data: {}, created_at: '' }),
    updateFixture: vi.fn().mockResolvedValue({}),
    deleteFixture: vi.fn().mockResolvedValue(undefined),
  },
}))

import { api } from '../api/client'

describe('UserProfiles', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    ;(api.listFixtures as ReturnType<typeof vi.fn>).mockResolvedValue([])
    ;(api.generateProfile as ReturnType<typeof vi.fn>).mockResolvedValue({
      name: 'Test User',
      data: {
        ageYears: 30,
        location: { city: 'Mumbai', state: 'Maharashtra', country: 'India' },
        monthlyIncomeRange: { min: 50000, max: 80000, currency: 'INR' },
        creditScore: { score: 750, maxScore: 900 },
        bankAccounts: [{ issuerName: 'HDFC Bank' }],
        cards: [{ issuerName: 'HDFC Bank', productName: 'Regalia', cardType: 'CREDIT', cardScheme: 'VISA' }],
      },
    })
    ;(api.generateTransactions as ReturnType<typeof vi.fn>).mockResolvedValue({
      transactions: [{ transactionId: 'tx1', counterpartyName: 'Store', amount: 100 }],
      count: 1,
    })
  })

  it('renders the page with profile list', async () => {
    render(<UserProfiles />)
    expect(screen.getByText('User Profiles')).toBeInTheDocument()
    expect(screen.getByText('New Profile')).toBeInTheDocument()
  })

  it('shows generating indicator when New Profile is clicked', async () => {
    let resolveProfile!: (v: unknown) => void
    ;(api.generateProfile as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((resolve) => { resolveProfile = resolve })
    )

    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    expect(screen.getByText(/generating random user profile/i)).toBeInTheDocument()

    // Resolve to avoid dangling promise
    resolveProfile({
      name: 'Test',
      data: {
        ageYears: 30, location: { city: 'X', state: 'Y', country: 'India' },
        monthlyIncomeRange: { min: 1, max: 2, currency: 'INR' },
        creditScore: { score: 1, maxScore: 900 },
        bankAccounts: [{ issuerName: 'B' }],
        cards: [{ issuerName: 'B', productName: 'C', cardType: 'CREDIT', cardScheme: 'VISA' }],
      },
    })
  })

  it('populates form after profile generation completes', async () => {
    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    // Wait for generation to complete and name to update
    const nameInput = await screen.findByPlaceholderText('Profile name')
    await waitFor(() => {
      expect(nameInput).toHaveValue('Test User')
    })
  })

  it('shows error on profile generation failure', async () => {
    ;(api.generateProfile as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('API down'))

    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    await waitFor(() => {
      expect(screen.getByText(/profile generation failed/i)).toBeInTheDocument()
    })
  })

  it('shows generate transactions panel when creating', async () => {
    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    await waitFor(() => {
      expect(screen.getByText('Generate Transactions')).toBeInTheDocument()
      expect(screen.getByText('Generate')).toBeInTheDocument()
    })
  })

  it('disables New Profile button while generating', async () => {
    let resolveProfile!: (v: unknown) => void
    ;(api.generateProfile as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((resolve) => { resolveProfile = resolve })
    )

    render(<UserProfiles />)
    await userEvent.click(screen.getByText('New Profile'))

    // Button should show "Generating..." and be disabled
    const btn = screen.getByText('Generating...')
    expect(btn).toBeDisabled()

    resolveProfile({
      name: 'X',
      data: {
        ageYears: 30, location: { city: 'X', state: 'Y', country: 'India' },
        monthlyIncomeRange: { min: 1, max: 2, currency: 'INR' },
        creditScore: { score: 1, maxScore: 900 },
        bankAccounts: [{ issuerName: 'B' }],
        cards: [{ issuerName: 'B', productName: 'C', cardType: 'CREDIT', cardScheme: 'VISA' }],
      },
    })
  })
})
