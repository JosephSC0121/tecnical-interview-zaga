import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Paper from '@mui/material/Paper'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Typography from '@mui/material/Typography'
import { listProjects } from '../api'
import type { ProjectSummary } from '../types'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; projects: ProjectSummary[] }

export default function ProjectListPage() {
  const [state, setState] = useState<State>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    listProjects().then(
      (projects) => !cancelled && setState({ status: 'ready', projects }),
      (error: Error) => !cancelled && setState({ status: 'error', message: error.message }),
    )
    return () => {
      cancelled = true
    }
  }, [attempt])

  const retry = () => {
    setState({ status: 'loading' })
    setAttempt((n) => n + 1)
  }

  if (state.status === 'loading') return <CircularProgress aria-label="Loading projects" />
  if (state.status === 'error') {
    return (
      <Alert severity="error" action={<Button onClick={retry}>Retry</Button>}>
        Could not load the projects: {state.message}
      </Alert>
    )
  }

  return (
    <>
      <Typography variant="h5" component="h1" gutterBottom>
        Projects ({state.projects.length})
      </Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Id</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Sector</TableCell>
              <TableCell>Country</TableCell>
              <TableCell>Stage</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {state.projects.map((project) => (
              <TableRow key={project.id} hover>
                <TableCell>
                  <Link to={`/projects/${encodeURIComponent(project.id)}`}>{project.id}</Link>
                </TableCell>
                <TableCell>{project.name}</TableCell>
                <TableCell>{project.sector}</TableCell>
                <TableCell>{project.country}</TableCell>
                <TableCell>{project.stage}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  )
}
