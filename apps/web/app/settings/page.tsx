'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Navigation } from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { CheckCircle2, XCircle } from 'lucide-react'

export default function SettingsPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('kommo')

  // Kommo connection state
  const [kommoInfo, setKommoInfo] = useState<any>(null)
  const [loadingKommo, setLoadingKommo] = useState(true)
  const [accessToken, setAccessToken] = useState('')
  const [refreshToken, setRefreshToken] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [errorKommo, setErrorKommo] = useState('')

  // Mapping state
  const [mapping, setMapping] = useState<any>({})
  const [loadingMapping, setLoadingMapping] = useState(true)
  const [savingMapping, setSavingMapping] = useState(false)
  const [mappingSuccess, setMappingSuccess] = useState(false)
  const [errorMapping, setErrorMapping] = useState('')

  useEffect(() => {
    const apiKey = localStorage.getItem('apiKey')
    if (!apiKey) {
      router.push('/login')
      return
    }
    fetchKommoInfo()
    fetchMapping()
  }, [])

  const fetchKommoInfo = async () => {
    setLoadingKommo(true)
    try {
      const info = await api.getKommoInfo()
      setKommoInfo(info)
    } catch (err: any) {
      setErrorKommo(err.message || 'Failed to fetch Kommo info')
    } finally {
      setLoadingKommo(false)
    }
  }

  const handleSaveTokens = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setErrorKommo('')
    setSaveSuccess(false)

    try {
      await api.pasteKommoTokens({
        access_token: accessToken,
        refresh_token: refreshToken,
        expires_at: expiresAt,
      })
      setSaveSuccess(true)
      setAccessToken('')
      setRefreshToken('')
      setExpiresAt('')
      fetchKommoInfo()
    } catch (err: any) {
      setErrorKommo(err.message || 'Failed to save tokens')
    } finally {
      setSaving(false)
    }
  }

  const fetchMapping = async () => {
    setLoadingMapping(true)
    try {
      const result = await api.getFieldMapping()
      setMapping(result.mapping)
    } catch (err: any) {
      setErrorMapping(err.message || 'Failed to fetch mapping')
    } finally {
      setLoadingMapping(false)
    }
  }

  const handleSaveMapping = async () => {
    setSavingMapping(true)
    setErrorMapping('')
    setMappingSuccess(false)

    try {
      await api.updateFieldMapping(mapping)
      setMappingSuccess(true)
    } catch (err: any) {
      setErrorMapping(err.message || 'Failed to save mapping')
    } finally {
      setSavingMapping(false)
    }
  }

  const handleMappingChange = (key: string, value: string) => {
    setMapping({ ...mapping, [key]: value || null })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Settings</h1>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="kommo">Kommo Integration</TabsTrigger>
            <TabsTrigger value="mapping">Field Mapping</TabsTrigger>
          </TabsList>

          <TabsContent value="kommo" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Connection Status</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingKommo ? (
                  <p>Loading...</p>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      {kommoInfo?.connected ? (
                        <>
                          <CheckCircle2 className="h-5 w-5 text-green-600" />
                          <Badge variant="default">Connected</Badge>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-5 w-5 text-red-600" />
                          <Badge variant="destructive">Not Connected</Badge>
                        </>
                      )}
                    </div>
                    
                    {kommoInfo?.connected && (
                      <>
                        <div>
                          <p className="text-sm text-muted-foreground">Base URL</p>
                          <p className="font-mono text-sm">{kommoInfo.base_url}</p>
                        </div>
                        {kommoInfo.expires_at && (
                          <div>
                            <p className="text-sm text-muted-foreground">Token Expires</p>
                            <p className="text-sm">{formatDate(kommoInfo.expires_at)}</p>
                          </div>
                        )}
                        {kommoInfo.account_info && (
                          <div>
                            <p className="text-sm text-muted-foreground">Account</p>
                            <p className="text-sm">{kommoInfo.account_info.name || 'Connected'}</p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Paste Tokens (MVP Mode)</CardTitle>
                <CardDescription>
                  Manually paste your Kommo OAuth tokens. Get these from your Kommo integration settings.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveTokens} className="space-y-4">
                  <div>
                    <Label htmlFor="accessToken">Access Token</Label>
                    <Input
                      id="accessToken"
                      type="text"
                      value={accessToken}
                      onChange={(e) => setAccessToken(e.target.value)}
                      placeholder="eyJ0eXAiOiJKV1QiLCJhbGc..."
                      required
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="refreshToken">Refresh Token</Label>
                    <Input
                      id="refreshToken"
                      type="text"
                      value={refreshToken}
                      onChange={(e) => setRefreshToken(e.target.value)}
                      placeholder="def50200..."
                      required
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="expiresAt">Expires At (ISO format)</Label>
                    <Input
                      id="expiresAt"
                      type="text"
                      value={expiresAt}
                      onChange={(e) => setExpiresAt(e.target.value)}
                      placeholder="2024-12-31T23:59:59Z"
                      required
                    />
                  </div>

                  {errorKommo && (
                    <div className="bg-destructive/10 text-destructive px-4 py-3 rounded text-sm">
                      {errorKommo}
                    </div>
                  )}

                  {saveSuccess && (
                    <div className="bg-green-50 text-green-700 px-4 py-3 rounded text-sm">
                      Tokens saved successfully!
                    </div>
                  )}

                  <Button type="submit" disabled={saving}>
                    {saving ? 'Saving...' : 'Save Tokens'}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="mapping" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Custom Field Mapping</CardTitle>
                <CardDescription>
                  Map extraction fields to Kommo custom field IDs. Leave empty to skip.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingMapping ? (
                  <p>Loading...</p>
                ) : (
                  <div className="space-y-4">
                    {Object.keys(mapping).map((key) => (
                      <div key={key}>
                        <Label htmlFor={key}>{key}</Label>
                        <Input
                          id={key}
                          type="text"
                          value={mapping[key] || ''}
                          onChange={(e) => handleMappingChange(key, e.target.value)}
                          placeholder="Kommo field ID (e.g., 12345)"
                        />
                      </div>
                    ))}

                    {errorMapping && (
                      <div className="bg-destructive/10 text-destructive px-4 py-3 rounded text-sm">
                        {errorMapping}
                      </div>
                    )}

                    {mappingSuccess && (
                      <div className="bg-green-50 text-green-700 px-4 py-3 rounded text-sm">
                        Mapping saved successfully!
                      </div>
                    )}

                    <Button onClick={handleSaveMapping} disabled={savingMapping}>
                      {savingMapping ? 'Saving...' : 'Save Mapping'}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Example Mapping</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto">
{`{
  "qualification.score": "12345",
  "qualification.budget": "12346",
  "qualification.timeline": "12347",
  "confidence": "12348"
}`}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}








