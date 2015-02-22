<!DOCTYPE html>
<html>
<head>
<title>HTML5 Cast Server</title>
</head>
<body>
<h1>{{listing_title}}</h1>
<table>
  <thead>
    <th>Name</th><th>Length</th>
  </thead>
%for id, name, length in items:
  <tr>
    <td><a href='/player/{{id}}'>{{name}}</a></td>
    <td>{{length}}</td>
  </tr>
%end
</table>
</body>
</html>
