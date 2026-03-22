import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

interface ColumnInfo {
  name: string;
  dtype: string;
}

interface UploadResponse {
  filename: string;
  columns: ColumnInfo[];
  preview: Record<string, unknown>[];
}

interface QueryResponse {
  query: string;
  result: Record<string, unknown>[] | null;
  error: string | null;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  // Upload state
  filename = '';
  columns: ColumnInfo[] = [];
  preview: Record<string, unknown>[] = [];
  uploading = false;
  uploadError = '';

  // Query state
  question = '';
  querying = false;
  generatedQuery = '';
  queryResult: Record<string, unknown>[] | null = null;
  queryError = '';

  constructor(private http: HttpClient) {}

  get previewHeaders(): string[] {
    return this.preview.length > 0 ? Object.keys(this.preview[0]) : [];
  }

  get resultHeaders(): string[] {
    return this.queryResult && this.queryResult.length > 0
      ? Object.keys(this.queryResult[0])
      : [];
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    this.uploading = true;
    this.uploadError = '';
    this.queryResult = null;
    this.queryError = '';
    this.generatedQuery = '';

    this.http.post<UploadResponse>('/upload', formData).subscribe({
      next: (res) => {
        this.filename = res.filename;
        this.columns = res.columns;
        this.preview = res.preview;
        this.uploading = false;
      },
      error: (err) => {
        this.uploadError = err.error?.detail || 'Upload failed.';
        this.uploading = false;
      },
    });
  }

  submitQuery(): void {
    if (!this.question.trim()) return;

    this.querying = true;
    this.queryError = '';
    this.queryResult = null;
    this.generatedQuery = '';

    this.http
      .post<QueryResponse>('/query', { question: this.question })
      .subscribe({
        next: (res) => {
          this.generatedQuery = res.query;
          if (res.error) {
            this.queryError = res.error;
          } else {
            this.queryResult = res.result;
          }
          this.querying = false;
        },
        error: (err) => {
          this.queryError = err.error?.detail || 'Query failed.';
          this.querying = false;
        },
      });
  }
}
