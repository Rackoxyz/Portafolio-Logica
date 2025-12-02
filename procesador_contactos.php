<?php
// ----------------------------------------------------------------------
// CONEXIÓN A BASE DE DATOS REMOTA (MV de Ubuntu - 192.168.56.10)
// ----------------------------------------------------------------------
$servername = "192.168.56.10"; 
$username = "app_user";
$password = "isaac.rick";
$dbname = "chinos_cafe";

// Crear conexión
$conn = new mysqli($servername, $username, $password, $dbname);

// Verificar conexión
if ($conn->connect_error) {
    die("Conexión fallida con el servidor de DB: " . $conn->connect_error);
}

// ----------------------------------------------------------------------
// PROCESAR DATOS DEL FORMULARIO
// ----------------------------------------------------------------------
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Usamos real_escape_string para prevenir inyección SQL (seguridad básica)
    $nombre = $conn->real_escape_string($_POST['nombre']);
    $email = $conn->real_escape_string($_POST['email']);
    $mensaje = $conn->real_escape_string($_POST['mensaje']);
    
    // Consulta de inserción
    $sql = "INSERT INTO Contactos (nombre, email, mensaje) VALUES ('$nombre', '$email', '$mensaje')";

    if ($conn->query($sql) === TRUE) {
        echo "<h1>✅ ¡Contacto Recibido!</h1>";
        echo "<p>Gracias, $nombre. Tu mensaje ha sido guardado exitosamente en la DB.</p>";
        echo "<p><a href='index.html'>Volver al formulario</a></p>";
    } else {
        echo "<h1>❌ Error:</h1> " . $sql . "<br>" . $conn->error;
    }
}

$conn->close();
?>