"""
Calibre Library Client
"""

import os
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from xml.etree import ElementTree as ET
from datetime import datetime

from ..key_manager import KeyManager


class CalibreClient:
    """Client for interacting with Calibre library"""

    def __init__(self, library_path: Optional[str] = None):
        if library_path is None:
            # Load from centralized keys
            self._key_manager = KeyManager()
            library_path = self._key_manager.get_calibre_library_path()
        self.library_path = Path(library_path)
        self.db_path = self.library_path / "metadata.db"
        
        if not self.library_path.exists():
            raise FileNotFoundError(f"Calibre library not found at: {library_path}")
        if not self.db_path.exists():
            raise FileNotFoundError(f"Calibre database not found at: {self.db_path}")
            
    def get_all_books(self) -> List[Dict[str, Any]]:
        """Get all books from Calibre database"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            
            # Main query to get book information
            query = """
            SELECT 
                b.id,
                b.title,
                b.sort,
                b.timestamp,
                b.pubdate,
                b.series_index,
                b.author_sort,
                b.isbn,
                b.lccn,
                b.path,
                b.flags,
                b.uuid,
                b.has_cover,
                GROUP_CONCAT(a.name, '|') as authors,
                GROUP_CONCAT(p.name, '|') as publishers,
                GROUP_CONCAT(t.name, '|') as tags,
                GROUP_CONCAT(s.name, '|') as series,
                GROUP_CONCAT(l.lang_code, '|') as languages,
                GROUP_CONCAT(i.val, '|') as identifiers,
                GROUP_CONCAT(i.type, '|') as identifier_types,
                c.text as comments,
                GROUP_CONCAT(d.name || ':' || d.format, '|') as formats
            FROM books b
            LEFT JOIN books_authors_link bal ON b.id = bal.book
            LEFT JOIN authors a ON bal.author = a.id
            LEFT JOIN books_publishers_link bpl ON b.id = bpl.book
            LEFT JOIN publishers p ON bpl.publisher = p.id
            LEFT JOIN books_tags_link btl ON b.id = btl.book
            LEFT JOIN tags t ON btl.tag = t.id
            LEFT JOIN books_series_link bsl ON b.id = bsl.book
            LEFT JOIN series s ON bsl.series = s.id
            LEFT JOIN books_languages_link bll ON b.id = bll.book
            LEFT JOIN languages l ON bll.lang_code = l.id
            LEFT JOIN identifiers i ON b.id = i.book
            LEFT JOIN comments c ON b.id = c.book
            LEFT JOIN data d ON b.id = d.book
            GROUP BY b.id
            ORDER BY b.title
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            books = []
            for row in rows:
                book = dict(row)
                
                # Parse grouped fields and remove duplicates
                book['authors'] = list(set(book['authors'].split('|'))) if book['authors'] else []
                book['publishers'] = list(set(book['publishers'].split('|'))) if book['publishers'] else []
                book['tags'] = list(set(book['tags'].split('|'))) if book['tags'] else []
                book['series'] = list(set(book['series'].split('|'))) if book['series'] else []
                book['languages'] = list(set(book['languages'].split('|'))) if book['languages'] else []
                
                # Parse identifiers
                if book['identifiers'] and book['identifier_types']:
                    id_vals = book['identifiers'].split('|')
                    id_types = book['identifier_types'].split('|')
                    book['parsed_identifiers'] = dict(zip(id_types, id_vals))
                else:
                    book['parsed_identifiers'] = {}
                
                # Parse formats
                if book['formats']:
                    format_pairs = book['formats'].split('|')
                    book['parsed_formats'] = {}
                    for pair in format_pairs:
                        if ':' in pair:
                            name, fmt = pair.split(':', 1)
                            book['parsed_formats'][fmt.upper()] = name
                else:
                    book['parsed_formats'] = {}
                
                books.append(book)
                
            return books
            
        finally:
            conn.close()
            
    def get_book_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific book by Calibre ID"""
        books = self.get_all_books()
        for book in books:
            if book['id'] == book_id:
                return book
        return None
        
    def get_book_metadata_from_opf(self, book_path: str) -> Dict[str, Any]:
        """Parse metadata.opf file for additional details"""
        opf_path = self.library_path / book_path / "metadata.opf"
        
        if not opf_path.exists():
            return {}
            
        try:
            tree = ET.parse(str(opf_path))
            root = tree.getroot()
            
            # Define namespaces
            ns = {
                'dc': 'http://purl.org/dc/elements/1.1/',
                'opf': 'http://www.idpf.org/2007/opf'
            }
            
            metadata = {}
            
            # Extract basic Dublin Core metadata
            for elem in root.find('.//{http://www.idpf.org/2007/opf}metadata'):
                if elem.tag.startswith('{http://purl.org/dc/elements/1.1/}'):
                    key = elem.tag.replace('{http://purl.org/dc/elements/1.1/}', 'dc_')
                    if key in metadata:
                        if not isinstance(metadata[key], list):
                            metadata[key] = [metadata[key]]
                        metadata[key].append(elem.text)
                    else:
                        metadata[key] = elem.text
                        
            # Extract Calibre custom metadata
            for meta in root.findall('.//{http://www.idpf.org/2007/opf}meta'):
                name = meta.get('name', '')
                content = meta.get('content', '')
                if name.startswith('calibre:'):
                    metadata[name.replace('calibre:', '')] = content
                    
            return metadata
            
        except ET.ParseError as e:
            print(f"Error parsing OPF file {opf_path}: {e}")
            return {}
            
    def get_cover_path(self, book_path: str) -> Optional[Path]:
        """Get the path to a book's cover image"""
        cover_path = self.library_path / book_path / "cover.jpg"
        if cover_path.exists():
            return cover_path
        return None
        
    def copy_cover_to_obsidian(self, book_path: str, obsidian_covers_dir: Path, 
                              filename: str) -> Optional[str]:
        """Copy book cover to Obsidian attachments directory"""
        cover_source = self.get_cover_path(book_path)
        
        if not cover_source:
            return None
            
        # Ensure covers directory exists
        obsidian_covers_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy cover with new filename
        cover_dest = obsidian_covers_dir / f"{filename}_cover.jpg"
        
        try:
            shutil.copy2(str(cover_source), str(cover_dest))
            print(f"  📥 Copied cover: {cover_dest.name}")
            return f"Attachments/book_covers/{cover_dest.name}"
        except Exception as e:
            print(f"  ⚠️  Failed to copy cover: {e}")
            return None
            
    def search_books(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search books by title or author"""
        all_books = self.get_all_books()
        
        query_lower = query.lower()
        matches = []
        
        for book in all_books:
            # Search in title
            if query_lower in book['title'].lower():
                matches.append(book)
                continue
                
            # Search in authors
            for author in book['authors']:
                if query_lower in author.lower():
                    matches.append(book)
                    break
                    
            # Search in series
            for series in book['series']:
                if query_lower in series.lower():
                    matches.append(book)
                    break
                    
        return matches[:limit]
        
    def get_reading_statistics(self) -> Dict[str, Any]:
        """Get statistics about the Calibre library"""
        books = self.get_all_books()
        
        stats = {
            'total_books': len(books),
            'authors': set(),
            'publishers': set(),
            'series': set(),
            'tags': set(),
            'languages': set(),
            'formats': set(),
            'books_with_covers': 0,
            'publication_years': []
        }
        
        for book in books:
            stats['authors'].update(book['authors'])
            stats['publishers'].update(book['publishers'])
            stats['series'].update(book['series'])
            stats['tags'].update(book['tags'])
            stats['languages'].update(book['languages'])
            stats['formats'].update(book['parsed_formats'].keys())
            
            if book['has_cover']:
                stats['books_with_covers'] += 1
                
            # Extract publication year
            if book['pubdate']:
                try:
                    pub_year = datetime.fromisoformat(book['pubdate'].replace('Z', '+00:00')).year
                    stats['publication_years'].append(pub_year)
                except:
                    pass
                    
        # Convert sets to counts
        stats['unique_authors'] = len(stats['authors'])
        stats['unique_publishers'] = len(stats['publishers'])
        stats['unique_series'] = len(stats['series'])
        stats['unique_tags'] = len(stats['tags'])
        stats['unique_languages'] = len(stats['languages'])
        stats['unique_formats'] = len(stats['formats'])
        
        # Year statistics
        if stats['publication_years']:
            stats['earliest_year'] = min(stats['publication_years'])
            stats['latest_year'] = max(stats['publication_years'])
        
        return stats