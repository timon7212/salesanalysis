'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function LoginPage() {
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!apiKey.trim()) {
      setError('API key is required')
      return
    }

    // Test the API key
    try {
      // Определяем API URL динамически на основе текущего hostname
      const isLocal = window.location.hostname === 'localhost' || 
                     window.location.hostname === '127.0.0.1'
      const API_URL = isLocal 
        ? 'http://localhost:8000' 
        : `http://${window.location.hostname}:8000`
      
      console.log('Hostname:', window.location.hostname)
      console.log('API URL:', API_URL)
      console.log('Testing API key...')
      
      const response = await fetch(`${API_URL}/health`, {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
        },
      })

      console.log('Response status:', response.status)
      console.log('Response ok:', response.ok)
      
      const data = await response.json()
      console.log('Response data:', data)

      if (response.ok) {
        console.log('Login successful, storing API key and redirecting...')
        // Store in localStorage
        localStorage.setItem('apiKey', apiKey)
        router.push('/leads')
      } else {
        setError('Invalid API key')
      }
    } catch (err) {
      console.error('Login error:', err)
      setError('Failed to connect to API: ' + (err as Error).message)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-3xl font-bold">Kommo Call Analyzer</CardTitle>
          <CardDescription>
            Enter your admin API key to continue
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key</Label>
              <Input
                id="apiKey"
                type="password"
                placeholder="Enter your ADMIN_API_KEY"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button type="submit" className="w-full">
              Sign In
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}








