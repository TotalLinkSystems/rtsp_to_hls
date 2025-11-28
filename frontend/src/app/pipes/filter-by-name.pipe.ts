import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'filterByName',
  pure: false // so it updates as you type
})
export class FilterByNamePipe implements PipeTransform {

  transform(records: any[], searchText: string): any[] {
    if (!records) return [];
    if (!searchText) return records;

    const lower = searchText.toLowerCase();

    return records.filter(rec =>
      rec.name.toLowerCase().includes(lower)
    );
  }
}
