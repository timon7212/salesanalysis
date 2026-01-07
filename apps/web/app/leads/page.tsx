'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Navigation } from '@/components/Navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Search, ChevronLeft, ChevronRight, Filter, X } from 'lucide-react'

export default function LeadsPage() {
  const router = useRouter()
  const [leads, setLeads] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20
  
  // Filters
  const [pipelines, setPipelines] = useState<any[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<number | undefined>()
  const [selectedUser, setSelectedUser] = useState<number | undefined>()
  const [showFilters, setShowFilters] = useState(false)
  
  // Map pipeline IDs to names
  const [pipelineMap, setPipelineMap] = useState<Record<number, string>>({})

  useEffect(() => {
    const apiKey = localStorage.getItem('apiKey')
    if (!apiKey) {
      router.push('/login')
      return
    }
    fetchFilters()
    fetchLeads()
  }, [page, selectedPipeline, selectedUser])

  const fetchFilters = async () => {
    try {
      const [pipelinesRes, usersRes] = await Promise.all([
        api.getPipelines(),
        api.getUsers()
      ])
      setPipelines(pipelinesRes.pipelines || [])
      setUsers(usersRes.users || [])
      
      // Build pipeline map
      const map: Record<number, string> = {}
      pipelinesRes.pipelines?.forEach((p: any) => {
        map[p.id] = p.name
      })
      setPipelineMap(map)
    } catch (err) {
      console.error('Failed to fetch filters:', err)
    }
  }

  const fetchLeads = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await api.getLeads(
        searchQuery || undefined, 
        page, 
        pageSize,
        selectedPipeline,
        selectedUser
      )
      setLeads(result.leads)
      setTotal(result.total)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch leads')
    } finally {
      setLoading(false)
    }
  }
  
  const clearFilters = () => {
    setSelectedPipeline(undefined)
    setSelectedUser(undefined)
    setSearchQuery('')
    setPage(1)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchLeads()
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Leads</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 mb-6">
              {/* Search and Filter Toggle */}
              <form onSubmit={handleSearch} className="flex gap-2">
                <Input
                  placeholder="Поиск по имени или ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit">
                  <Search className="h-4 w-4 mr-2" />
                  Поиск
                </Button>
                <Button 
                  type="button"
                  variant={showFilters ? "default" : "outline"}
                  onClick={() => setShowFilters(!showFilters)}
                >
                  <Filter className="h-4 w-4 mr-2" />
                  Фильтры
                  {(selectedPipeline || selectedUser) && (
                    <Badge className="ml-2 bg-primary-foreground text-primary">
                      {[selectedPipeline, selectedUser].filter(Boolean).length}
                    </Badge>
                  )}
                </Button>
              </form>

              {/* Filters */}
              {showFilters && (
                <Card className="bg-muted/50">
                  <CardContent className="pt-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Pipeline Filter */}
                      <div className="space-y-2">
                        <Label htmlFor="pipeline-filter">Воронка</Label>
                        <select
                          id="pipeline-filter"
                          value={selectedPipeline || ''}
                          onChange={(e) => {
                            setSelectedPipeline(e.target.value ? parseInt(e.target.value) : undefined)
                            setPage(1)
                          }}
                          className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <option value="">Все воронки</option>
                          {pipelines.map((pipeline) => (
                            <option key={pipeline.id} value={pipeline.id}>
                              {pipeline.name}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* User Filter */}
                      <div className="space-y-2">
                        <Label htmlFor="user-filter">Ответственный</Label>
                        <select
                          id="user-filter"
                          value={selectedUser || ''}
                          onChange={(e) => {
                            setSelectedUser(e.target.value ? parseInt(e.target.value) : undefined)
                            setPage(1)
                          }}
                          className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <option value="">Все пользователи</option>
                          {users.map((user) => (
                            <option key={user.id} value={user.id}>
                              {user.name}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Clear Filters */}
                      <div className="flex items-end">
                        <Button 
                          type="button"
                          variant="outline" 
                          onClick={clearFilters}
                          className="w-full"
                          disabled={!selectedPipeline && !selectedUser && !searchQuery}
                        >
                          <X className="h-4 w-4 mr-2" />
                          Очистить
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            {error && (
              <div className="bg-destructive/10 text-destructive px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            {loading ? (
              <div className="text-center py-8">Loading...</div>
            ) : leads.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No leads found. Make sure Kommo is connected in Settings.
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>Название</TableHead>
                      <TableHead>Воронка</TableHead>
                      <TableHead>Контакт</TableHead>
                      <TableHead>Сумма</TableHead>
                      <TableHead>Создан</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leads.map((lead) => (
                      <TableRow key={lead.lead_id}>
                        <TableCell className="font-mono text-sm">{lead.lead_id}</TableCell>
                        <TableCell className="font-medium">{lead.lead_name}</TableCell>
                        <TableCell>
                          {lead.pipeline_id && pipelineMap[lead.pipeline_id] ? (
                            <Badge variant="outline" className="text-xs">
                              {pipelineMap[lead.pipeline_id]}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground text-sm">-</span>
                          )}
                        </TableCell>
                        <TableCell>{lead.contact_name || '-'}</TableCell>
                        <TableCell>{lead.price ? `$${lead.price}` : '-'}</TableCell>
                        <TableCell className="text-sm">{lead.created_at ? formatDate(lead.created_at) : '-'}</TableCell>
                        <TableCell>
                          <Link href={`/leads/${lead.lead_id}`}>
                            <Button size="sm" variant="outline">Открыть</Button>
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <div className="text-sm text-muted-foreground">
                      Page {page} of {totalPages} ({total} total)
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}


