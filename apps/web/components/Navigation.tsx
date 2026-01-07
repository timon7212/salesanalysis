'use client'

import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Phone, Settings, LogOut } from 'lucide-react'

export function Navigation() {
  const router = useRouter()
  const pathname = usePathname()

  const handleLogout = () => {
    localStorage.removeItem('apiKey')
    router.push('/login')
  }

  return (
    <nav className="border-b bg-white">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link href="/leads" className="flex items-center space-x-2">
            <Phone className="h-6 w-6 text-primary" />
            <span className="font-bold text-xl">Kommo Call Analyzer</span>
          </Link>
          <div className="flex space-x-2">
            <Link href="/leads">
              <Button variant={pathname?.startsWith('/leads') ? 'default' : 'ghost'}>
                Leads
              </Button>
            </Link>
            <Link href="/settings">
              <Button variant={pathname?.startsWith('/settings') ? 'default' : 'ghost'}>
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </Button>
            </Link>
          </div>
        </div>
        <Button variant="ghost" onClick={handleLogout}>
          <LogOut className="h-4 w-4 mr-2" />
          Logout
        </Button>
      </div>
    </nav>
  )
}








