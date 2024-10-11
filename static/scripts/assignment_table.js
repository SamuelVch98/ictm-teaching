import { fixedHeaders, fixedRowsText, ColumnIndices, RowIndices, lenFixedRowsText, lenFixedHeaders, borderStyle, requiredProperties, taLoad, phdLoad, postDocLoad } from './constants.js';

fetch('/assignment/load_data')
    .then(response => response.json())
    .then(loadData => {

        const {courses, users, teachers, researchers, supervisors, preferences, organizations, current_year} = loadData;
        courses.forEach(course => {
            let teachersId = Object.values(teachers).filter(teacher => teacher.course_id === course.id);
            let teachersName = teachersId.map(teacher => {
                let teacherUser = users[teacher.user_id];
                return teacherUser ? `${teacherUser.name} ${teacherUser.first_name}` : '';
            });
            course.assigned_teachers = teachersName.join(', ');
        });

        //Split long text in the course header
        const coursesHeaders = courses.map(course => {
            const maxLength = 30;
            const courseName = course.title;

            if (courseName.length > maxLength) {
                const firstLine = courseName.substring(0, maxLength / 2);
                const secondLine = courseName.substring(maxLength / 2);
                const finalResult = `${secondLine}<br>${firstLine}<br>${course.code}`;
                return finalResult
            } else {
                const finalResult = `${courseName}<br>${course.code}`;
                return finalResult;
            }
        });

        //Create all course header
        const allHeaders = fixedHeaders.concat(coursesHeaders);

        function fixedRowsData() {
            let rows = [];

            const allProperties = Object.keys(courses[0]);
            const properties = allProperties.filter(prop => requiredProperties.includes(prop));
            // Use to keep the order of the properties
            const orderedProperties = requiredProperties.map(prop => properties.includes(prop) ? prop : null).filter(prop => prop !== null);
            orderedProperties.push('tutors')

            for (let i = 0; i < lenFixedRowsText; i++) {
                let row = {
                    researchers: {
                        id: "",
                        name: ""
                    },
                    org: "",
                    promoter: "",
                    totalLoad: "",
                    loadQ1: "",
                    loadQ2: ""
                };

                courses.forEach(course => {
                    row[course.code] = orderedProperties.includes('tutors') && orderedProperties[i] === 'tutors' ? 0 : course[orderedProperties[i]];
                });
                rows.push(row);
            }

            return rows;
        }

        function buildRow(user, isFilled) {
            const row = {};
            row.researchers = {
                id: user.id,
                name: isFilled ? `${user.name} ${user.first_name}` : ""
            };
            return row;
        }

        function userRowsData() {
            const rows = [];

            for (const researcherId in researchers) {
                const researcher = researchers[researcherId];
                const user = users[researcher.user_id];
                //The first line displays the preferences for each user
                const row = buildRow(user, true);
                //The second line allows admins to assign a course to the user
                const emptyRow = buildRow(user, false);
                //const matchingAssistant = researchers[user.id];
                const assistantOrg = organizations[user.organization_id];

                let researcherSupervisor = Object.values(supervisors).filter(supervisor => supervisor.researcher_id === researcher.id);
                let supervisorNames = researcherSupervisor.map(supervisor => {
                    let user = users[supervisor.supervisor_id];
                    return user ? `${user.name}` : '';
                });
                researcher.promoters = supervisorNames.join(', ');

                row.org = assistantOrg ? assistantOrg.name : "";
                row.promoter = researcher.promoters;
                row.totalLoad = researcher.max_loads;
                row.loadQ1 = 0;
                row.loadQ2 = 0;

                //This line is only used to store course assignments, so the other values are empty.
                const emptyKeys = ['org', 'promoter', 'totalLoad', 'loadQ1', 'loadQ2'];
                emptyKeys.forEach(key => {
                    emptyRow[key] = "";
                });

                const userPrefs = Object.values(preferences).filter(pref => pref.researcher_id === researcher.id);

                let pos = 1;
                courses.forEach(course => {
                    const isPref = userPrefs.find(pref => pref.course_id === course.id);
                    const code = course.code;
                    row[code] = isPref ? pos++ : "";
                    emptyRow[code] = "";
                });

                rows.push(row);
                rows.push(emptyRow);
            }
            return rows;
        }

        const fixedRows = fixedRowsData();
        const userRows = userRowsData();


        function getCourseColumns() {
            const fixedColumns = [
                {data: 'researchers.id'},
                {data: 'researchers.name'},
                {data: 'org'},
                {data: 'promoter'},
                {data: 'totalLoad'},
                {data: 'loadQ1'},
                {data: 'loadQ2'}
            ];

            courses.forEach(course => {
                const code = course.code;
                let col = {data: code};
                fixedColumns.push(col)
            });
            return fixedColumns;
        }

        const columns = getCourseColumns();

        let data = fixedRows.concat(userRows);
        const nbrLines = data.length - 1;
        const nbrCols = columns.length - 1;

        const mergeCellsSettings = [];
        for (let row = lenFixedRowsText; row < nbrLines; row += 2) {
            for (let col = 1; col <= lenFixedHeaders - 1; col++) {
                mergeCellsSettings.push({
                    row: row,
                    col: col,
                    rowspan: 2,
                    colspan: 1
                });
            }
        }

        function storeDataLocally(data) {
            localStorage.setItem('table', JSON.stringify(data));
        }

        function storeCellsMeta(cellsMeta) {
            localStorage.setItem('cellsMeta', JSON.stringify(cellsMeta));
        }

        function retrieveDataLocally() {
            const storedData = localStorage.getItem('table');
            if (storedData) {
                data = JSON.parse(storedData);
            }
        }

        function retrieveCellsMetaLocally() {
            const cellsMeta = localStorage.getItem('cellsMeta');
            return cellsMeta ? JSON.parse(cellsMeta) : null;
        }

        function resetDataLocally() {
            localStorage.clear();
        }

        // Verify if the table is modified locally
        retrieveDataLocally();
        let comments = retrieveCellsMetaLocally();
        let isCollectedMetaData = true;

        const table = new Handsontable(document.getElementById("handsontable"), {
            data: data,
            fixedColumnsLeft: lenFixedHeaders,
            fixedRowsTop: lenFixedRowsText,
            manualColumnMove: true,
            manualColumnResize: true,
            manualRowResize: true,
            mergeCells: mergeCellsSettings,
            comments: true,
            hiddenColumns: {
                columns: [0],
                indicators: true,
            },
            hiddenRows: {
                rows: [0],
                indicators: true,
            },
            contextMenu: ['commentsAddEdit', 'commentsRemove', 'hidden_columns_hide', 'hidden_rows_hide', 'hidden_columns_show', 'hidden_rows_show'],
            filters: true,
            dropdownMenu: ['filter_by_value', 'filter_action_bar', 'undo'],
            className: 'controlsQuickFilter htCenter htMiddle',
            colHeaders: allHeaders,
            columns: columns,
            colWidths: 100,
            columnHeaderHeight: 225,
            rowHeaders: fixedRowsText,
            rowHeaderWidth: 125,
            init: function () {
                if (comments) {
                    comments.forEach(comment => {
                        this.setCellMeta(comment.row, comment.col, comment.key, comment.value);
                    });
                }
                isCollectedMetaData = false;
            },
            afterGetColHeader: function (col, th) {
                th.style.transform = 'rotate(180deg)';
                th.style.writingMode = 'vertical-lr';
                th.style.textAlign = 'center';
                th.style.fontWeight = 'bold';
                th.style.height = '100px';
                th.style.lineHeight = '100px';

                if (col > lenFixedHeaders - 1) {
                    let colData = this.getDataAtCol(col);
                    if (colData[RowIndices.TOTAL_ASSISTANT_NOW] >= colData[RowIndices.ASSISTANTS]) {
                        th.style.backgroundColor = 'green';
                    }
                }
            },
            afterChange: function (changes) {
                if (changes) {
                    changes.forEach(([row, prop, oldValue, newValue]) => {
                        let col = this.propToCol(prop);
                        if ((col >= lenFixedHeaders && row >= lenFixedRowsText) && (row % 2 === 1)) {

                            const colInfos = this.getDataAtProp(prop);
                            let nbrAssistants = colInfos[RowIndices.TOTAL_ASSISTANT_NOW];
                            const rowInfos = this.getDataAtRow(row - 1);
                            const quadri = colInfos[RowIndices.QUADRI];

                            let loadKey = quadri === 1 ? ColumnIndices.LOAD_Q1 : ColumnIndices.LOAD_Q2;
                            let loadValue = rowInfos[loadKey];

                            // Old non-empty value and new empty value: loadValue-- and nbrAssistants--.
                            // Old non-empty value and new non-empty value: loadValue++ and nbrAssistants++.
                            // Old null value and new non-empty value: loadValue++ and nbrAssistants++.
                            // Old non-null value and new null value: loadValue-- and nbrAssistants--.
                            if (oldValue !== newValue) {
                                if ((oldValue !== '' && newValue === '') || (oldValue !== null && newValue === null)) {
                                    if (loadValue > 0 && nbrAssistants > 0) {
                                        loadValue--;
                                        nbrAssistants--;
                                    }
                                } else if ((oldValue === '' && newValue !== '') || (oldValue === null && newValue !== null)) {
                                    loadValue++;
                                    nbrAssistants++;
                                }
                                this.setDataAtCell(row - 1, loadKey, loadValue);
                                this.setDataAtCell(RowIndices.TOTAL_ASSISTANT_NOW, col, nbrAssistants);
                            }
                        }
                    });
                }
            },
            afterSetCellMeta: function (row, col, key, value) {
                if (key === 'comment' && !isCollectedMetaData) {
                    let comments = JSON.parse(localStorage.getItem('cellsMeta')) || [];
                    const comment = {'row': row, 'col': col, 'key': key, 'value': value};
                    comments.push(comment);
                    storeCellsMeta(comments);
                }
            },
            afterRenderer: function (TD, row, col, prop, value, cellProperties) {
                if ((col >= lenFixedHeaders && row >= lenFixedRowsText) && (row % 2 === 1) && (value !== '')) {
                    TD.style.fontWeight = 'bold'; // Bold text
                    TD.style.textAlign = 'left'; // Left alignment
                }
                //Style first col if needed
                if (col === 0 && row < lenFixedRowsText) {
                    TD.style.fontWeight = 'bold';
                    TD.style.textAlign = 'left';
                }
                //(row%2) === 1 to avoid empty lines
                if (row >= lenFixedRowsText && (row % 2) === 0 && col < lenFixedHeaders) {
                    const rowValue = this.getDataAtRow(row);
                    if (col === ColumnIndices.LOAD_Q1 || col === ColumnIndices.LOAD_Q2) {
                        const total_load = rowValue[ColumnIndices.TOTAL_LOAD];
                        const load_q1 = rowValue[ColumnIndices.LOAD_Q1];
                        const load_q2 = rowValue[ColumnIndices.LOAD_Q2];

                        //First case: load Q1 + Q2 = total load
                        //Second case: load Q1 or Q2 = half of total load
                        if (load_q1 + load_q2 > total_load) {
                            TD.style.backgroundColor = 'red';
                        } else if ((total_load === taLoad || total_load === phdLoad) && (total_load / value <= phdLoad || load_q1 + load_q2 === total_load)) {
                            TD.style.backgroundColor = 'green';
                        } else if (total_load === postDocLoad) {
                            if (value === postDocLoad) {
                                TD.style.backgroundColor = 'green';
                            } else {
                                if ((load_q1 === postDocLoad && load_q2 === 0) || (load_q1 === 0 && load_q2 === postDocLoad)) {
                                    TD.style.backgroundColor = 'green';
                                }
                            }
                        }
                    }
                }
            },
            customBorders: [
                {
                    range: {
                        from: {row: 0, col: 0},
                        to: {row: nbrLines, col: 6}
                    },
                    end: borderStyle,
                },
                {
                    range: {
                        from: {row: 0, col: 0},
                        to: {row: 5, col: nbrCols}
                    },
                    bottom: borderStyle,
                },
                {
                    row: 5,
                    col: 6,
                    bottom: borderStyle
                },
            ],
            beforeFilter(conditionsStack) {
                const filtersPlugin = this.getPlugin('filters');
                //Get the user data without the fixed rows
                const tab = this.getData().slice(lenFixedRowsText);

                let values = [];
                const filteredResults = [];
                //Get the number of the column to filter

                if (conditionsStack && conditionsStack.length > 0) {
                    const col = conditionsStack[0].column;

                    if (conditionsStack && conditionsStack.length > 0) {
                        for (let i = 0; i < conditionsStack.length; i++) {
                            //Get the matching values to filter
                            values = conditionsStack[i].conditions[0].args.flat();

                            //Verify if the row value for the specific column is in the filter
                            for (const row of tab) {
                                if (values.includes(row[col])) {
                                    //Push id to the filteredResults array
                                    filteredResults.push(row[0]);
                                }
                            }
                        }
                    }
                    filtersPlugin.clearConditions();
                    //Create a new condition to filter the data based on the id
                    filtersPlugin.addCondition(0, 'by_value', [filteredResults]);
                }
            },
            afterFilter(conditionsStack) {
                const filtersPlugin = this.getPlugin('filters');
                const filtersRowsMap = filtersPlugin.filtersRowsMap;

                // Exclude fixed lines from the filter
                for (let i = 0; i < lenFixedRowsText; i++) {
                    filtersRowsMap.setValueAtIndex(i, false);
                }
            },
            licenseKey: "non-commercial-and-evaluation",
        });

        $(document).ready(function () {
            // Disable the cells that contain user preferences
            table.updateSettings({
                cells: function (row, col) {
                    let cellProperties = {};
                    // Row % 2 === 0 to get the user preferences
                    if (row >= lenFixedRowsText && col >= lenFixedHeaders && row % 2 === 0) {
                        cellProperties.readOnly = true;
                    }
                    return cellProperties;
                }
            });
            function updateToastContent(message) {
                let toastBody = document.querySelector('#toast-notification .toast-body');
                toastBody.textContent = message;
            }

            let toastNotification = new bootstrap.Toast(document.getElementById('toast-notification'));

            $('#button-export').click(function () {
                const exportPlugin = table.getPlugin('exportFile');
                exportPlugin.downloadFile('csv', {
                    bom: false,
                    columnDelimiter: ',',
                    columnHeaders: true,
                    exportHiddenColumns: false,
                    exportHiddenRows: false,
                    fileExtension: 'csv',
                    filename: 'ICTM-CSV-file_[YYYY]-[MM]-[DD]',
                    mimeType: 'text/csv',
                    rowDelimiter: '\r\n',
                    rowHeaders: true
                });
                updateToastContent('Data exported to CSV');
                toastNotification.show();
            })
            $('#button-create-assignments').click(function () {
                storeDataLocally(data);
                updateToastContent('Data saved');
                toastNotification.show();
            });
            $('#button-clear-assignments').click(function () {
                resetDataLocally();
                updateToastContent('Data cleared');
                toastNotification.show();
                setTimeout(function () {
                    location.reload();
                }, 1500);
            })

            async function handlePublish(publicationType) {
                const teacherPublication = (publicationType === 'teacher');
                const slicedData = data.slice(lenFixedRowsText);
                const result = [];

                for (let i = 0; i < slicedData.length; i += 2) {
                    const user_row = slicedData[i];
                    const course_row = slicedData[i + 1];

                    const userData = {
                        user_id: user_row.researchers.id,
                        load_q1: user_row.loadQ1,
                        load_q2: user_row.loadQ2,
                        teacher_publication: teacherPublication,
                    };

                    const courseData = {};
                    courses.forEach(course => {
                        if (course_row[course.code] !== '') {
                            courseData[course.id] = course_row[course.code];
                        }
                    })
                    result.push({userData, courseData});
                }

                try {
                    const response = await fetch('/assignment/publish_assignments', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(result),
                    });

                    if (response.ok) {
                        updateToastContent('Assignments published');
                        toastNotification.show();
                    } else {
                        updateToastContent('Failed to publish assignments' + response.statusText);
                        toastNotification.show();
                    }
                } catch (error) {
                    updateToastContent('Error: ' + error);
                    toastNotification.show();
                }
            }

            $('#button-publish-teachers').click(function () {
                handlePublish('teacher'); // Pour les enseignants
            });

            $('#button-publish-everyone').click(function () {
                handlePublish('everyone'); // Pour tout le monde
            });

            /*
            $('#button-publish-assignments').click(async function () {
                const publicationType = $(this).data('publication');
                const teacherPublication = (publicationType === 'teacher');

                const slicedData = data.slice(lenFixedRowsText);
                const result = [];

                for (let i = 0; i < slicedData.length; i += 2) {
                    const user_row = slicedData[i];
                    const course_row = slicedData[i + 1];

                    const userData = {
                        user_id: user_row.researchers.id,
                        load_q1: user_row.loadQ1,
                        load_q2: user_row.loadQ2,
                        teacher_publication: teacherPublication,
                    };

                    const courseData = {};
                    courses.forEach(course => {
                        if (course_row[course.code] !== '') {
                            courseData[course.id] = course_row[course.code];
                        }
                    })
                    result.push({userData, courseData});
                }

                try {
                    const response = await fetch('/assignment/publish_assignments', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(result),
                    });

                    if (response.ok) {
                        updateToastContent('Assignments published');
                        toastNotification.show();
                    } else {
                        updateToastContent('Failed to publish assignments' + response.statusText);
                        toastNotification.show();
                    }
                } catch (error) {
                    updateToastContent('Error: ' + error);
                    toastNotification.show();
                }
            });
             */
        });
    });

